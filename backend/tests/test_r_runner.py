
from pathlib import Path

import pytest

from app.analysis.r_runner import RAnalysisError, run_limma


ROOT = Path(__file__).resolve().parents[2]
EXPRESSION = ROOT / "backend" / "r" / "test_expression.tsv"
DESIGN = ROOT / "backend" / "r" / "test_design.tsv"


def test_run_limma_returns_valid_results():
    result = run_limma(EXPRESSION, DESIGN)

    assert result["engine"] == "limma"
    assert result["features_tested"] == 5
    assert result["contrast"] == "Tumour-Normal"
    assert result["significance_threshold"] == 0.05

    genes = {item["gene_id"]: item for item in result["results"]}
    assert genes["GENE_A"]["direction"] == "Tumour_up"
    assert genes["GENE_B"]["direction"] == "Normal_up"
    assert genes["GENE_C"]["direction"] == "not_significant"


def test_run_limma_rejects_missing_expression_file():
    with pytest.raises(RAnalysisError, match="Expression matrix file"):
        run_limma(ROOT / "missing_expression.tsv", DESIGN)


def test_run_limma_rejects_missing_design_file():
    with pytest.raises(RAnalysisError, match="Sample design file"):
        run_limma(EXPRESSION, ROOT / "missing_design.tsv")


def test_run_limma_rejects_nonpositive_timeout():
    with pytest.raises(ValueError, match="timeout_seconds"):
        run_limma(EXPRESSION, DESIGN, timeout_seconds=0)
