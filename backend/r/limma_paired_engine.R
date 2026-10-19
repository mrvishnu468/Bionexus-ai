
# BioNexus Omni: paired differential expression using limma.
# Expression input: TSV, genes in rows, samples in columns.
# Design TSV: sample_id, group, patient_id.
# CLI: Rscript limma_paired_engine.R expression.tsv design.tsv output.tsv numerator denominator

run_paired_limma <- function(
    expression,
    metadata,
    numerator_group,
    denominator_group,
    adjusted_p_cutoff = 0.05
) {
    if (!requireNamespace("limma", quietly = TRUE)) {
        stop("The Bioconductor package 'limma' is required.")
    }

    if (!is.matrix(expression) || !is.numeric(expression)) {
        stop("Expression must be a numeric matrix.")
    }
    if (is.null(rownames(expression)) || is.null(colnames(expression))) {
        stop("Expression must have gene and sample names.")
    }
    if (any(!is.finite(expression))) {
        stop("Expression contains missing or non-finite values.")
    }
    if (!is.numeric(adjusted_p_cutoff) ||
        length(adjusted_p_cutoff) != 1L ||
        !is.finite(adjusted_p_cutoff) ||
        adjusted_p_cutoff <= 0 ||
        adjusted_p_cutoff > 1) {
        stop("adjusted_p_cutoff must be greater than 0 and at most 1.")
    }

    required <- c("sample_id", "group", "patient_id")
    if (!all(required %in% names(metadata))) {
        stop("Design requires sample_id, group, and patient_id.")
    }

    metadata <- as.data.frame(metadata, stringsAsFactors = FALSE)
    metadata$sample_id <- trimws(as.character(metadata$sample_id))
    metadata$group <- trimws(as.character(metadata$group))
    metadata$patient_id <- trimws(as.character(metadata$patient_id))

    if (anyNA(metadata[, required]) ||
        any(!nzchar(metadata$sample_id)) ||
        any(!nzchar(metadata$group)) ||
        any(!nzchar(metadata$patient_id))) {
        stop("Design fields must be non-empty.")
    }
    if (anyDuplicated(metadata$sample_id)) {
        stop("Duplicate sample assignments are not allowed.")
    }
    if (anyDuplicated(rownames(expression))) {
        stop("Duplicate gene identifiers are not allowed.")
    }

    missing_samples <- setdiff(metadata$sample_id, colnames(expression))
    if (length(missing_samples)) {
        stop("Design samples missing from expression matrix: ",
             paste(missing_samples, collapse = ", "))
    }

    # Only researcher-approved paired samples belong in this design.
    expression <- expression[, metadata$sample_id, drop = FALSE]

    if (length(unique(metadata$group)) != 2L ||
        !all(c(numerator_group, denominator_group) %in%
             unique(metadata$group)) ||
        identical(numerator_group, denominator_group)) {
        stop("Exactly the two requested comparison groups are required.")
    }

    metadata <- metadata[
        match(colnames(expression), metadata$sample_id),
        ,
        drop = FALSE
    ]

    metadata$group <- factor(
        metadata$group,
        levels = c(denominator_group, numerator_group)
    )
    metadata$patient_id <- factor(metadata$patient_id)

    pair_table <- table(
        metadata$patient_id,
        metadata$group
    )

    if (nrow(pair_table) < 2L) {
        stop("At least two complete patient pairs are required.")
    }
    if (any(pair_table != 1L)) {
        stop("Each patient must have exactly one sample in each group.")
    }

    design <- stats::model.matrix(~ patient_id + group, data = metadata)
    if (qr(design)$rank != ncol(design)) {
        stop("Paired design matrix is not full rank.")
    }

    group_coefficients <- grep("^group", colnames(design), value = TRUE)
    if (length(group_coefficients) != 1L) {
        stop("Could not uniquely identify the group coefficient.")
    }

    fit <- limma::lmFit(expression, design)
    fit <- limma::eBayes(fit)

    table_results <- limma::topTable(
        fit,
        coef = group_coefficients[[1]],
        number = Inf,
        adjust.method = "BH",
        sort.by = "P"
    )

    direction <- ifelse(
        table_results$logFC > 0,
        "up_in_numerator",
        ifelse(table_results$logFC < 0,
               "up_in_denominator", "unchanged")
    )

    results <- data.frame(
        gene_id = rownames(table_results),
        log2_fold_change = table_results$logFC,
        average_expression = table_results$AveExpr,
        moderated_t = table_results$t,
        p_value = table_results$P.Value,
        adjusted_p_value = table_results$adj.P.Val,
        B_statistic = table_results$B,
        direction = direction,
        contrast = paste(numerator_group, "vs", denominator_group),
        stringsAsFactors = FALSE,
        check.names = FALSE
    )

    list(
        results = results,
        patient_count = nrow(pair_table),
        sample_count = nrow(metadata),
        method = "limma_paired_patient_block",
        adjusted_p_cutoff = adjusted_p_cutoff
    )
}

if (sys.nframe() == 0L) {
    args <- commandArgs(trailingOnly = TRUE)
    if (length(args) != 5L) {
        stop("Expected: expression.tsv design.tsv output.tsv numerator denominator")
    }

    expression_df <- read.delim(
        args[[1]], row.names = 1, check.names = FALSE,
        stringsAsFactors = FALSE
    )
    expression <- as.matrix(expression_df)
    suppressWarnings(storage.mode(expression) <- "numeric")

    if (any(!is.finite(expression))) {
        stop("Expression file contains non-numeric or non-finite values.")
    }

    metadata <- read.delim(
        args[[2]], check.names = FALSE,
        stringsAsFactors = FALSE
    )

    result <- run_paired_limma(
        expression = expression,
        metadata = metadata,
        numerator_group = args[[4]],
        denominator_group = args[[5]]
    )

    write.table(
        result$results,
        file = args[[3]],
        sep = "\t",
        quote = FALSE,
        row.names = FALSE,
        col.names = TRUE
    )

    message(
        "Paired limma completed: ",
        result$patient_count, " patient pairs; ",
        result$sample_count, " samples; ",
        nrow(result$results), " genes."
    )
}
