from app.models.experimental_design import ExperimentalDesign


class ExperimentalDesignEvaluator:
    def evaluate(self, design: ExperimentalDesign) -> tuple[bool, list[str]]:
        reasons: list[str] = []

        if not design.metadata_complete:
            reasons.append("Experimental metadata is incomplete.")

        if not design.has_control_group:
            reasons.append("No control group is available for comparison.")

        if not design.has_biological_replicates:
            reasons.append("Biological replicates are not confirmed.")

        if len(design.groups) < 2:
            reasons.append("At least two experimental groups are required.")

        for group in design.groups:
            if group.sample_count < 2:
                reasons.append(
                    f"Group '{group.name}' has fewer than two samples."
                )

        is_suitable = len(reasons) == 0

        return is_suitable, reasons


experimental_design_evaluator = ExperimentalDesignEvaluator()