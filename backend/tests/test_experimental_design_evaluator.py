from app.models.experimental_design import (
    ExperimentalDesign,
    ExperimentalGroup,
)
from app.services.experimental_design_evaluator import (
    experimental_design_evaluator,
)


def test_valid_case_control_design_is_suitable():
    design = ExperimentalDesign(
        groups=[
            ExperimentalGroup(name="Control", sample_count=3),
            ExperimentalGroup(name="Disease", sample_count=3),
        ],
        has_biological_replicates=True,
        has_control_group=True,
        metadata_complete=True,
    )

    suitable, reasons = experimental_design_evaluator.evaluate(design)

    assert suitable is True
    assert reasons == []


def test_single_group_design_is_not_suitable():
    design = ExperimentalDesign(
        groups=[
            ExperimentalGroup(name="Disease", sample_count=3),
        ],
        has_biological_replicates=True,
        has_control_group=False,
        metadata_complete=True,
    )

    suitable, reasons = experimental_design_evaluator.evaluate(design)

    assert suitable is False
    assert "No control group is available for comparison." in reasons


def test_single_sample_group_is_not_suitable():
    design = ExperimentalDesign(
        groups=[
            ExperimentalGroup(name="Control", sample_count=1),
            ExperimentalGroup(name="Disease", sample_count=3),
        ],
        has_biological_replicates=True,
        has_control_group=True,
        metadata_complete=True,
    )

    suitable, reasons = experimental_design_evaluator.evaluate(design)

    assert suitable is False
    assert any("fewer than two samples" in reason for reason in reasons)
def test_named_tissue_groups_are_not_automatically_approved_as_control():
    design = ExperimentalDesign(
        groups=[
            ExperimentalGroup(
                name="early breast cancer",
                sample_count=6,
            ),
            ExperimentalGroup(
                name="matched adjacent non-tumor tissue",
                sample_count=6,
            ),
        ],
        has_biological_replicates=True,
        has_control_group=True,
        metadata_complete=True,
    )

    suitable, reasons = experimental_design_evaluator.evaluate(design)

    assert suitable is False
    assert "No control group is available for comparison." in reasons