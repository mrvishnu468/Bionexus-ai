
#!/usr/bin/env Rscript

# BioNexus Omni: microarray differential-expression engine
# Input: expression matrix TSV, sample design TSV, output TSV
# Optional arguments: numerator group, denominator group
# Design columns: sample_id, group
# Expression matrix: first column gene_id, remaining columns sample IDs

fail <- function(message, code = 1L) {
  cat(paste0("BioNexus limma error: ", message, "\n"), file = stderr())
  quit(save = "no", status = code)
}

args <- commandArgs(trailingOnly = TRUE)

if (!(length(args) %in% c(3L, 5L))) {
  fail(
    paste(
      "Usage:",
      "Rscript limma_engine.R expression.tsv design.tsv results.tsv",
      "[numerator_group denominator_group]"
    )
  )
}

expression_path <- args[[1]]
design_path <- args[[2]]
results_path <- args[[3]]

explicit_contrast <- length(args) == 5L
numerator_group <- if (explicit_contrast) args[[4]] else NULL
denominator_group <- if (explicit_contrast) args[[5]] else NULL

if (explicit_contrast &&
    (!nzchar(trimws(numerator_group)) ||
     !nzchar(trimws(denominator_group)) ||
     identical(numerator_group, denominator_group))) {
  fail("Contrast groups must be non-empty and distinct.")
}

if (!requireNamespace("limma", quietly = TRUE)) {
  fail("Required Bioconductor package 'limma' is not installed.")
}

if (!file.exists(expression_path)) {
  fail("Expression matrix file does not exist.")
}

if (!file.exists(design_path)) {
  fail("Sample design file does not exist.")
}

expression_data <- tryCatch(
  read.delim(
    expression_path,
    check.names = FALSE,
    stringsAsFactors = FALSE,
    quote = "",
    comment.char = ""
  ),
  error = function(e) fail(paste("Cannot read expression matrix:", e$message))
)

design_data <- tryCatch(
  read.delim(
    design_path,
    check.names = FALSE,
    stringsAsFactors = FALSE,
    quote = "",
    comment.char = ""
  ),
  error = function(e) fail(paste("Cannot read sample design:", e$message))
)

if (ncol(expression_data) < 3L) {
  fail("Expression matrix must contain a feature ID and at least two samples.")
}

if (!"sample_id" %in% names(design_data) ||
    !"group" %in% names(design_data)) {
  fail("Design must contain sample_id and group columns.")
}

if (anyDuplicated(names(expression_data))) {
  fail("Expression matrix contains duplicate column names.")
}

if (anyDuplicated(expression_data[[1]])) {
  fail("Expression matrix contains duplicate feature IDs.")
}

if (anyNA(expression_data[[1]]) ||
    any(!nzchar(trimws(as.character(expression_data[[1]]))))) {
  fail("Feature IDs must be present and non-empty.")
}

if (anyDuplicated(design_data$sample_id)) {
  fail("Sample design contains duplicate sample IDs.")
}

if (anyNA(design_data$sample_id) ||
    any(!nzchar(trimws(as.character(design_data$sample_id))))) {
  fail("Sample IDs must be present and non-empty.")
}

if (anyNA(design_data$group) ||
    any(!nzchar(trimws(as.character(design_data$group))))) {
  fail("Group labels must be present and non-empty.")
}

sample_ids <- as.character(design_data$sample_id)
matrix_sample_ids <- names(expression_data)[-1]

if (!setequal(sample_ids, matrix_sample_ids)) {
  fail("Design sample IDs must match expression matrix columns exactly.")
}

# Reorder expression columns to match design rows.
expression_data <- expression_data[
  ,
  c(names(expression_data)[1], sample_ids),
  drop = FALSE
]

expression_matrix <- as.matrix(expression_data[, -1, drop = FALSE])
storage.mode(expression_matrix) <- "numeric"
rownames(expression_matrix) <- as.character(expression_data[[1]])

if (any(!is.finite(expression_matrix))) {
  fail("Expression matrix contains missing, non-numeric, or non-finite values.")
}

if (nrow(expression_matrix) < 2L) {
  fail("At least two features are required.")
}

if (ncol(expression_matrix) != nrow(design_data)) {
  fail("Expression and design dimensions do not agree.")
}

# Preserve the sample design's group labels.
group_labels <- as.character(design_data$group)
group <- factor(group_labels, levels = unique(group_labels))

if (nlevels(group) != 2L) {
  fail("This initial engine requires exactly two confirmed groups.")
}

group_counts <- table(group)

if (any(group_counts < 2L)) {
  fail("Each group must contain at least two biological samples.")
}

design <- model.matrix(~ 0 + group)
colnames(design) <- levels(group)

if (qr(design)$rank != ncol(design)) {
  fail("Experimental design is not full rank.")
}

# An explicit contrast is numerator minus denominator.
# The legacy three-argument interface retains its prior default ordering.
if (explicit_contrast) {
  if (!(numerator_group %in% levels(group)) ||
      !(denominator_group %in% levels(group))) {
    fail("Both contrast groups must exist in the confirmed sample design.")
  }
} else {
  numerator_group <- levels(group)[2]
  denominator_group <- levels(group)[1]
}

contrast_text <- paste0(numerator_group, "-", denominator_group)

contrast_matrix <- matrix(
  0,
  nrow = ncol(design),
  ncol = 1,
  dimnames = list(colnames(design), contrast_text)
)

contrast_matrix[numerator_group, 1] <- 1
contrast_matrix[denominator_group, 1] <- -1

fit <- limma::lmFit(expression_matrix, design)
fit <- limma::contrasts.fit(fit, contrast_matrix)
fit <- limma::eBayes(fit)

results <- limma::topTable(
  fit,
  coef = 1,
  number = Inf,
  adjust.method = "BH",
  sort.by = "none"
)

results$gene_id <- rownames(results)

results <- results[
  ,
  c("gene_id", "logFC", "AveExpr", "t", "P.Value", "adj.P.Val", "B"),
  drop = FALSE
]

names(results) <- c(
  "gene_id",
  "log2_fold_change",
  "average_expression",
  "moderated_t",
  "p_value",
  "adjusted_p_value",
  "B_statistic"
)

results$direction <- ifelse(
  results$adjusted_p_value < 0.05 & results$log2_fold_change > 0,
  paste0(numerator_group, "_up"),
  ifelse(
    results$adjusted_p_value < 0.05 & results$log2_fold_change < 0,
    paste0(denominator_group, "_up"),
    "not_significant"
  )
)

results$contrast <- contrast_text

write.table(
  results,
  file = results_path,
  sep = "\t",
  quote = FALSE,
  row.names = FALSE,
  col.names = TRUE,
  na = "NA"
)

cat(
  paste0(
    "BioNexus limma completed: ",
    nrow(results),
    " features tested; contrast ",
    contrast_text,
    ".\n"
  )
)
