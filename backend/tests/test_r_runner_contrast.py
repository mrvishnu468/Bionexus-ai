
from __future__ import annotations

import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.analysis.r_runner import run_limma


RESULTS_TSV = (
    "gene_id\tlog2_fold_change\taverage_expression\tmoderated_t\t"
    "p_value\tadjusted_p_value\tB_statistic\tdirection\tcontrast\n"
    "GENE_A\t2.0\t8.0\t5.0\t0.001\t0.01\t3.0\tTumour_up\tTumour-Normal\n"
    "GENE_B\t-1.5\t6.0\t-4.0\t0.002\t0.02\t2.0\tNormal_up\tTumour-Normal\n"
)


def prepare_inputs(tmp_path: Path) -> tuple[Path, Path, Path]:
    expression = tmp_path / "expression.tsv"
    design = tmp_path / "design.tsv"
    script = tmp_path / "limma_engine.R"

    expression.write_text("gene_id\tS1\tS2\nGENE_A\t1\t2\n", encoding="utf-8")
    design.write_text(
        "sample_id\tgroup\nS1\tNormal\nS2\tTumour\n",
        encoding="utf-8",
    )
    script.write_text("# Test script placeholder\n", encoding="utf-8")

    return expression, design, script


def fake_successful_r(command, **kwargs):
    output_path = Path(command[4])
    output_path.write_text(RESULTS_TSV, encoding="utf-8")

    return SimpleNamespace(
        returncode=0,
        stdout="BioNexus limma completed.",
        stderr="",
    )


def test_explicit_contrast_groups_are_passed_to_r(tmp_path):
    expression, design, script = prepare_inputs(tmp_path)

    with patch(
        "app.analysis.r_runner.subprocess.run",
        side_effect=fake_successful_r,
    ) as mocked_run:
        result = run_limma(
            expression,
            design,
            script_path=script,
            rscript_path="Rscript-test",
            numerator_group="Tumour",
            denominator_group="Normal",
        )

    command = mocked_run.call_args.args[0]

    assert command[-2:] == ["Tumour", "Normal"]
    assert result["contrast"] == "Tumour-Normal"
    assert result["features_tested"] == 2
    assert mocked_run.call_args.kwargs["shell"] is False


def test_legacy_call_keeps_three_argument_r_interface(tmp_path):
    expression, design, script = prepare_inputs(tmp_path)

    with patch(
        "app.analysis.r_runner.subprocess.run",
        side_effect=fake_successful_r,
    ) as mocked_run:
        result = run_limma(
            expression,
            design,
            script_path=script,
            rscript_path="Rscript-test",
        )

    command = mocked_run.call_args.args[0]

    assert len(command) == 5
    assert result["contrast"] == "Tumour-Normal"


def test_missing_contrast_group_is_rejected():
    with pytest.raises(ValueError, match="supplied together"):
        run_limma(
            "expression.tsv",
            "design.tsv",
            numerator_group="Tumour",
        )


@pytest.mark.parametrize(
    ("numerator", "denominator"),
    [
        ("", "Normal"),
        ("Tumour", ""),
        ("Tumour", "Tumour"),
        ("   ", "Normal"),
    ],
)
def test_invalid_contrast_groups_are_rejected(numerator, denominator):
    with pytest.raises(ValueError, match="non-empty and distinct"):
        run_limma(
            "expression.tsv",
            "design.tsv",
            numerator_group=numerator,
            denominator_group=denominator,
        )
