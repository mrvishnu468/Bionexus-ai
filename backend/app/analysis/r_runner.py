from __future__ import annotations
import csv
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any


class RAnalysisError(RuntimeError):
    """Raised when the R differential-expression engine fails."""


RESULT_COLUMNS = (
    "gene_id",
    "log2_fold_change",
    "average_expression",
    "moderated_t",
    "p_value",
    "adjusted_p_value",
    "B_statistic",
    "direction",
    "contrast",
)


def _find_rscript() -> str:
    """Find Rscript without requiring a Windows PATH change."""
    candidates = [
        Path(r"C:\Program Files\R\R-4.6.1\bin\x64\Rscript.exe"),
        Path(r"C:\Program Files\R\R-4.6.1\bin\Rscript.exe"),
    ]

    for candidate in candidates:
        if candidate.is_file():
            return str(candidate)

    discovered = shutil.which("Rscript")
    if discovered:
        return discovered

    raise RAnalysisError(
        "Rscript was not found. Configure the Rscript executable path."
    )


def _read_results(path: Path) -> list[dict[str, Any]]:
    """Read and validate the TSV emitted by the R engine."""
    if not path.is_file():
        raise RAnalysisError("The R engine did not create a results file.")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")

        if reader.fieldnames is None:
            raise RAnalysisError("The results file has no header.")

        missing = set(RESULT_COLUMNS) - set(reader.fieldnames)
        if missing:
            raise RAnalysisError(
                f"Results file is missing columns: {', '.join(sorted(missing))}"
            )

        results: list[dict[str, Any]] = []

        for row in reader:
            parsed: dict[str, Any] = {
                "gene_id": row["gene_id"],
                "direction": row["direction"],
                "contrast": row["contrast"],
            }

            for column in RESULT_COLUMNS:
                if column in {"gene_id", "direction", "contrast"}:
                    continue

                try:
                    value = float(row[column])
                except (TypeError, ValueError) as exc:
                    raise RAnalysisError(
                        f"Invalid numeric value in result column {column}."
                    ) from exc

                parsed[column] = value

            results.append(parsed)

    if not results:
        raise RAnalysisError("The R engine returned no gene results.")

    return results


def run_limma(
    expression_path: str | Path,
    design_path: str | Path,
    *,
    script_path: str | Path | None = None,
    rscript_path: str | None = None,
    timeout_seconds: int = 120,
    numerator_group: str | None = None,
    denominator_group: str | None = None,
) -> dict[str, Any]:
    """Run limma with an optional researcher-selected contrast.

    The explicit contrast is numerator_group minus denominator_group.
    If neither group is supplied, retain the legacy R-script behavior.
    """
    if (numerator_group is None) != (denominator_group is None):
        raise ValueError(
            "numerator_group and denominator_group must be supplied together."
        )

    if numerator_group is not None and denominator_group is not None:
        if (
            not numerator_group.strip()
            or not denominator_group.strip()
            or numerator_group.strip() == denominator_group.strip()
        ):
            raise ValueError(
                "Contrast groups must be non-empty and distinct."
            )

    expression_file = Path(expression_path).resolve()
    design_file = Path(design_path).resolve()

    script_file = (
        Path(script_path).resolve()
        if script_path is not None
        else Path(__file__).resolve().parents[2] / "r" / "limma_engine.R"
    )

    executable = rscript_path or _find_rscript()

    if not expression_file.is_file():
        raise RAnalysisError("Expression matrix file does not exist.")

    if not design_file.is_file():
        raise RAnalysisError("Sample design file does not exist.")

    if not script_file.is_file():
        raise RAnalysisError(f"R engine script not found: {script_file}")

    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    with tempfile.TemporaryDirectory(prefix="bionexus-limma-") as temp_dir:
        output_file = Path(temp_dir) / "results.tsv"

        command = [
            executable,
            str(script_file),
            str(expression_file),
            str(design_file),
            str(output_file),
        ]

        if numerator_group is not None and denominator_group is not None:
            command.extend([numerator_group, denominator_group])

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RAnalysisError(
                f"R analysis exceeded the {timeout_seconds}-second timeout."
            ) from exc
        except OSError as exc:
            raise RAnalysisError(f"Could not start Rscript: {exc}") from exc

        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise RAnalysisError(
                details or f"R analysis exited with code {completed.returncode}."
            )

        results = _read_results(output_file)

        return {
            "engine": "limma",
            "contrast": results[0]["contrast"],
            "features_tested": len(results),
            "significance_threshold": 0.05,
            "results": results,
            "stdout": completed.stdout.strip(),
        }

def run_paired_limma(
    expression_path: str | Path,
    design_path: str | Path,
    *,
    approved_pairs: list[dict[str, Any]],
    numerator_group: str,
    denominator_group: str,
    script_path: str | Path | None = None,
    rscript_path: str | None = None,
    timeout_seconds: int = 120,
) -> dict[str, Any]:
    """Run paired limma only on explicitly approved, complete patient pairs."""
    import csv

    if not numerator_group.strip() or not denominator_group.strip():
        raise ValueError("Contrast groups must be non-empty.")
    if numerator_group.strip() == denominator_group.strip():
        raise ValueError("Contrast groups must be distinct.")
    if not approved_pairs:
        raise ValueError("At least one researcher-approved pair is required.")
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive.")

    expression_file = Path(expression_path).resolve()
    design_file = Path(design_path).resolve()
    script_file = (
        Path(script_path).resolve()
        if script_path is not None
        else Path(__file__).resolve().parents[2]
        / "r"
        / "limma_paired_engine.R"
    )

    for path, label in (
        (expression_file, "Expression matrix"),
        (design_file, "Sample design"),
        (script_file, "Paired R engine"),
    ):
        if not path.is_file():
            raise RAnalysisError(f"{label} file not found: {path}")

    seen_samples: set[str] = set()
    expected: dict[str, tuple[str, str]] = {}

    for pair in approved_pairs:
        if pair.get("approved") is not True:
            raise ValueError("Every pair must have explicit researcher approval.")

        patient = str(
            pair.get("patient_id_candidate") or pair.get("patient_id") or ""
        ).strip()
        tumour = str(pair.get("tumour_accession") or "").strip()
        normal = str(pair.get("normal_accession") or "").strip()

        if not patient or not tumour or not normal or tumour == normal:
            raise ValueError("Each approved pair needs a patient ID and two distinct samples.")

        if tumour in seen_samples or normal in seen_samples:
            raise ValueError("A sample cannot occur in more than one approved pair.")

        seen_samples.update((tumour, normal))
        expected[tumour] = (numerator_group, patient)
        expected[normal] = (denominator_group, patient)

    with design_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        required = {"sample_id", "group", "patient_id"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise RAnalysisError(
                "Paired design TSV requires sample_id, group, and patient_id columns."
            )
        rows = list(reader)

    observed: dict[str, tuple[str, str]] = {}
    for row in rows:
        sample_id = (row.get("sample_id") or "").strip()
        group = (row.get("group") or "").strip()
        patient = (row.get("patient_id") or "").strip()

        if not sample_id or not group or not patient:
            raise RAnalysisError("Paired design contains empty required fields.")
        if sample_id in observed:
            raise RAnalysisError(f"Duplicate design sample: {sample_id}")

        observed[sample_id] = (group, patient)

    if observed != expected:
        raise RAnalysisError(
            "Design assignments must exactly match approved pairs, "
            "including sample IDs, groups, and patient IDs."
        )

    executable = rscript_path or _find_rscript()

    with tempfile.TemporaryDirectory(prefix="bionexus-paired-limma-") as temp_dir:
        output_file = Path(temp_dir) / "results.tsv"
        command = [
            executable,
            str(script_file),
            str(expression_file),
            str(design_file),
            str(output_file),
            numerator_group,
            denominator_group,
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout_seconds,
                check=False,
                shell=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise RAnalysisError(
                f"Paired R analysis exceeded the {timeout_seconds}-second timeout."
            ) from exc
        except OSError as exc:
            raise RAnalysisError(f"Could not start Rscript: {exc}") from exc

        if completed.returncode != 0:
            details = completed.stderr.strip() or completed.stdout.strip()
            raise RAnalysisError(
                details or f"Paired R analysis exited with code {completed.returncode}."
            )

        results = _read_results(output_file)

        return {
            "engine": "limma_paired",
            "contrast": results[0]["contrast"],
            "features_tested": len(results),
            "significance_threshold": 0.05,
            "patient_pairs": len(approved_pairs),
            "samples_analyzed": len(seen_samples),
            "results": results,
            "stdout": completed.stdout.strip(),
        }
