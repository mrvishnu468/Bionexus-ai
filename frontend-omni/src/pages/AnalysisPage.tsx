import { useEffect, useMemo, useState } from "react";
import { readResearchContext } from "../services/researchContext";
import {
  executeGeoAnalysis,
  prepareGeoAnalysis,
  validateGeoMatrix,
  type GeoApprovedPair,
  type GeoDifferentialExpressionRow,
  type GeoExecutionResponse,
  type GeoPreparedAnalysis,
  type GeoSampleAssignment,
  type GeoValidationResponse,
} from "../services/api";
import "../styles/pages.css";
import "../styles/analysis.css";
import "../styles/analysis-tabs.css";

type WorkflowStage = "validation" | "design" | "pairing" | "results";
type ResultFilter = "all" | "significant" | "positive" | "negative";

const DEFAULT_ACCESSION = "GSE10072";

const ANALYSIS_STORAGE_KEY = "bionexus-analysis-session-v1";

type PersistedAnalysisState = {
  accession: string;
  validation: GeoValidationResponse | null;
  prepared: GeoPreparedAnalysis | null;
  execution: GeoExecutionResponse | null;
  assignments: GeoSampleAssignment[];
  numeratorGroup: string;
  denominatorGroup: string;
  normalizationConfirmed: boolean;
  designConfirmed: boolean;
  assignmentsReviewed: boolean;
  pairedAnalysis: boolean;
  approvedPairs: GeoApprovedPair[];
  stage: WorkflowStage;
  filter: ResultFilter;
};

function readAnalysisState(): Partial<PersistedAnalysisState> {
  try {
    const saved = localStorage.getItem(ANALYSIS_STORAGE_KEY);
    if (!saved) return {};

    const parsed: unknown = JSON.parse(saved);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }

    return parsed as Partial<PersistedAnalysisState>;
  } catch {
    return {};
  }
}

function formatNumber(value: number, digits = 4): string {
  if (!Number.isFinite(value)) return "—";
  return value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

function formatPValue(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value === 0) return "< 1e-300";
  if (value < 0.001) return value.toExponential(2);
  return value.toFixed(4);
}

function negativeLog10(value: number): number {
  return -Math.log10(Math.max(value, 1e-300));
}

function VolcanoPlot({
  rows,
  threshold,
}: {
  rows: GeoDifferentialExpressionRow[];
  threshold: number;
}) {
  const width = 760;
  const height = 340;
  const margin = { top: 20, right: 24, bottom: 54, left: 66 };
  const plotWidth = width - margin.left - margin.right;
  const plotHeight = height - margin.top - margin.bottom;

  const points = useMemo(() => {
    const step = Math.max(1, Math.ceil(rows.length / 2500));
    return rows.filter((_, index) => index % step === 0);
  }, [rows]);

  const maxX = Math.max(
    1,
    ...points.map((row) => Math.abs(row.log2_fold_change)),
  );
  const maxY = Math.max(
    2,
    ...points.map((row) =>
      negativeLog10(row.adjusted_p_value),
    ),
  );

  const xPosition = (value: number) =>
    margin.left + ((value + maxX) / (2 * maxX)) * plotWidth;

  const yPosition = (value: number) =>
    margin.top + plotHeight - (value / maxY) * plotHeight;

  const cutoffY = yPosition(negativeLog10(threshold));

  return (
    <div className="analysis-chart-scroll">
      <svg
        className="analysis-volcano"
        viewBox={`0 0 ${width} ${height}`}
        role="img"
        aria-label="Volcano plot of log2 fold change against negative log10 adjusted p-value"
      >
        {[0, 0.25, 0.5, 0.75, 1].map((fraction) => {
          const y = margin.top + fraction * plotHeight;
          const value = maxY * (1 - fraction);

          return (
            <g key={fraction}>
              <line
                x1={margin.left}
                y1={y}
                x2={width - margin.right}
                y2={y}
                stroke="var(--color-border)"
                strokeDasharray="3 5"
              />
              <text
                x={margin.left - 10}
                y={y + 4}
                textAnchor="end"
                fill="var(--color-text-muted)"
                fontSize="11"
              >
                {formatNumber(value, 1)}
              </text>
            </g>
          );
        })}

        <line
          x1={xPosition(0)}
          y1={margin.top}
          x2={xPosition(0)}
          y2={margin.top + plotHeight}
          stroke="var(--color-border)"
        />

        {cutoffY >= margin.top &&
          cutoffY <= margin.top + plotHeight && (
            <g>
              <line
                x1={margin.left}
                y1={cutoffY}
                x2={width - margin.right}
                y2={cutoffY}
                stroke="#D99A42"
                strokeDasharray="6 4"
              />
              <text
                x={width - margin.right - 4}
                y={cutoffY - 6}
                textAnchor="end"
                fill="#D99A42"
                fontSize="11"
              >
                Adjusted p = {threshold}
              </text>
            </g>
          )}

        {points.map((row, index) => {
          const significant =
            row.adjusted_p_value < threshold;
          const color = significant
            ? row.log2_fold_change >= 0
              ? "#DC6262"
              : "#4A90D9"
            : "#9CA3AF";

          return (
            <circle
              key={`${row.gene_id}-${index}`}
              cx={xPosition(row.log2_fold_change)}
              cy={yPosition(
                negativeLog10(row.adjusted_p_value),
              )}
              r={significant ? 2.5 : 1.7}
              fill={color}
              fillOpacity={significant ? 0.82 : 0.48}
            >
              <title>
                {`${row.gene_id} | log2FC: ${formatNumber(row.log2_fold_change)} | adjusted p: ${formatPValue(row.adjusted_p_value)}`}
              </title>
            </circle>
          );
        })}

        <line
          x1={margin.left}
          y1={margin.top + plotHeight}
          x2={width - margin.right}
          y2={margin.top + plotHeight}
          stroke="var(--color-border)"
        />

        <text
          x={margin.left + plotWidth / 2}
          y={height - 12}
          textAnchor="middle"
          fill="var(--color-text-muted)"
          fontSize="12"
        >
          log2 fold change
        </text>

        <text
          transform={`translate(17 ${margin.top + plotHeight / 2}) rotate(-90)`}
          textAnchor="middle"
          fill="var(--color-text-muted)"
          fontSize="12"
        >
          −log10 adjusted p-value
        </text>
      </svg>

      <div className="analysis-legend">
        <span>
          <i
            className="analysis-legend-dot"
            style={{ background: "#DC6262" }}
          />
          Positive log2 fold change
        </span>
        <span>
          <i
            className="analysis-legend-dot"
            style={{ background: "#4A90D9" }}
          />
          Negative log2 fold change
        </span>
        <span>
          <i
            className="analysis-legend-dot"
            style={{ background: "#9CA3AF" }}
          />
          Not significant
        </span>
      </div>

      <p className="analysis-muted">
        Plot points are sampled for display when there are more than
        2,500 tested features. The results table retains the returned
        analysis results.
      </p>
    </div>
  );
}

export function AnalysisPage() {
  const [initialSavedState] = useState(() => {
    const saved = readAnalysisState();
    const context = readResearchContext();
    const selected = context?.selectedDataset?.accession?.toUpperCase();
    const current = (saved.accession ?? DEFAULT_ACCESSION).toUpperCase();
    if (selected && /^GSE\d+$/.test(selected) && selected !== current) {
      return { accession: selected };
    }
    return saved;
  });
  const [accession, setAccession] = useState(initialSavedState.accession ?? DEFAULT_ACCESSION);
  const [validation, setValidation] =
    useState<GeoValidationResponse | null>(initialSavedState.validation ?? null);
  const [prepared, setPrepared] =
    useState<GeoPreparedAnalysis | null>(initialSavedState.prepared ?? null);
  const [execution, setExecution] =
    useState<GeoExecutionResponse | null>(initialSavedState.execution ?? null);

  const [assignments, setAssignments] =
    useState<GeoSampleAssignment[]>(initialSavedState.assignments ?? []);
  const [numeratorGroup, setNumeratorGroup] = useState(initialSavedState.numeratorGroup ?? "");
  const [denominatorGroup, setDenominatorGroup] = useState(initialSavedState.denominatorGroup ?? "");
  const [normalizationConfirmed, setNormalizationConfirmed] =
    useState(initialSavedState.normalizationConfirmed ?? false);
  const [designConfirmed, setDesignConfirmed] = useState(initialSavedState.designConfirmed ?? false);
  const [assignmentsReviewed, setAssignmentsReviewed] =
    useState(initialSavedState.assignmentsReviewed ?? false);

  const [pairedAnalysis, setPairedAnalysis] = useState(initialSavedState.pairedAnalysis ?? false);
  const [approvedPairs, setApprovedPairs] =
    useState<GeoApprovedPair[]>(initialSavedState.approvedPairs ?? []);

  const [stage, setStage] = useState<WorkflowStage>(initialSavedState.stage ?? "validation");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [filter, setFilter] = useState<ResultFilter>(initialSavedState.filter ?? "all");

  useEffect(() => {
    const savedState: PersistedAnalysisState = {
      accession,
      validation,
      prepared,
      execution,
      assignments,
      numeratorGroup,
      denominatorGroup,
      normalizationConfirmed,
      designConfirmed,
      assignmentsReviewed,
      pairedAnalysis,
      approvedPairs,
      stage,
      filter,
    };

    try {
      localStorage.setItem(
        ANALYSIS_STORAGE_KEY,
        JSON.stringify(savedState),
      );
    } catch (error) {
      console.error("Unable to save Analysis workspace state:", error);
    }
  }, [
    accession,
    validation,
    prepared,
    execution,
    assignments,
    numeratorGroup,
    denominatorGroup,
    normalizationConfirmed,
    designConfirmed,
    assignmentsReviewed,
    pairedAnalysis,
    approvedPairs,
    stage,
    filter,
  ]);

  const groupNames = useMemo(
    () =>
      [
        ...new Set(
          assignments
            .map((item) => item.group.trim())
            .filter(Boolean),
        ),
      ].sort(),
    [assignments],
  );

  const resultRows = execution?.results.results ?? [];
  const significanceThreshold =
    execution?.results.significance_threshold ?? 0.05;

  const significantRows = useMemo(
    () =>
      resultRows.filter(
        (row) => row.adjusted_p_value < significanceThreshold,
      ),
    [resultRows, significanceThreshold],
  );

  const positiveCount = significantRows.filter(
    (row) => row.log2_fold_change > 0,
  ).length;

  const negativeCount = significantRows.filter(
    (row) => row.log2_fold_change < 0,
  ).length;

  const visibleRows = useMemo(() => {
    const filtered = resultRows.filter((row) => {
      if (filter === "significant") {
        return row.adjusted_p_value < significanceThreshold;
      }
      if (filter === "positive") {
        return (
          row.adjusted_p_value < significanceThreshold &&
          row.log2_fold_change > 0
        );
      }
      if (filter === "negative") {
        return (
          row.adjusted_p_value < significanceThreshold &&
          row.log2_fold_change < 0
        );
      }
      return true;
    });

    return [...filtered].sort(
      (a, b) => a.adjusted_p_value - b.adjusted_p_value,
    );
  }, [resultRows, filter, significanceThreshold]);

  const assignedCount = assignments.filter(
    (item) => item.group.trim().length > 0,
  ).length;

  const validPairs = useMemo(() => {
    const seenSamples = new Set<string>();
    const seenPatients = new Set<string>();

    return approvedPairs.filter((pair) => {
      const tumour = pair.tumour_accession.trim();
      const normal = pair.normal_accession.trim();
      const patient = pair.patient_id.trim();

      if (
        !pair.approved ||
        !tumour ||
        !normal ||
        !patient ||
        tumour === normal ||
        seenSamples.has(tumour) ||
        seenSamples.has(normal) ||
        seenPatients.has(patient)
      ) {
        return false;
      }

      const tumourAssignment = assignments.find(
        (item) => item.sample_accession === tumour,
      );
      const normalAssignment = assignments.find(
        (item) => item.sample_accession === normal,
      );

      if (
        tumourAssignment?.group !== numeratorGroup ||
        normalAssignment?.group !== denominatorGroup
      ) {
        return false;
      }

      seenSamples.add(tumour);
      seenSamples.add(normal);
      seenPatients.add(patient);
      return true;
    });
  }, [
    approvedPairs,
    assignments,
    numeratorGroup,
    denominatorGroup,
  ]);

  const canExecute =
    Boolean(prepared) &&
    assignments.length >= 4 &&
    assignedCount === assignments.length &&
    groupNames.length >= 2 &&
    Boolean(numeratorGroup) &&
    Boolean(denominatorGroup) &&
    numeratorGroup !== denominatorGroup &&
    normalizationConfirmed &&
    designConfirmed &&
    assignmentsReviewed &&
    (!pairedAnalysis ||
      (validPairs.length >= 2 &&
        validPairs.length === approvedPairs.length)) &&
    !loading;

  async function handleValidate() {
    const id = accession.trim().toUpperCase();

    if (!id) {
      setError("Enter a GEO Series accession, such as GSE10072.");
      return;
    }

    setLoading(true);
    setError("");
    setNotice("");
    setValidation(null);
    setPrepared(null);
    setExecution(null);
    setAssignments([]);
    setApprovedPairs([]);
    setPairedAnalysis(false);
    setStage("validation");
    setAssignmentsReviewed(false);
    setDesignConfirmed(false);
    setNormalizationConfirmed(false);
    setNumeratorGroup("");
    setDenominatorGroup("");

    try {
      const result = await validateGeoMatrix(id);
      setValidation(result);

      if (result.errors.length > 0) {
        setError(result.errors.join(" "));
      } else {
        setNotice(
          result.ready_for_design_review
            ? "Matrix validation completed. Continue to sample and design review."
            : "Validation returned, but the matrix is not ready for design review.",
        );
      }
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "GEO matrix validation failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  async function handlePrepare() {
    if (!validation?.ready_for_design_review) {
      setError(
        "Validate a suitable GEO matrix before preparing the analysis.",
      );
      return;
    }

    setLoading(true);
    setError("");
    setNotice("");

    try {
      const result = await prepareGeoAnalysis(
        accession.trim().toUpperCase(),
      );

      setPrepared(result);
      setExecution(null);
      setApprovedPairs([]);
      setPairedAnalysis(false);

      const initialAssignments =
        result.design_review.group_assignments.map((item) => ({
          sample_accession: item.sample_accession,
          group: item.confirmed_group ?? item.suggested_group ?? "",
        }));

      setAssignments(initialAssignments);

      const suggestedGroups =
        result.design_review.suggested_groups.map(
          (group) => group.name,
        );

      setNumeratorGroup(suggestedGroups[0] ?? "");
      setDenominatorGroup(suggestedGroups[1] ?? "");
      setAssignmentsReviewed(false);
      setDesignConfirmed(false);
      setNormalizationConfirmed(false);
      setStage("design");

      setNotice(
        "Review every sample assignment. Suggestions are not researcher approval.",
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Could not prepare the GEO analysis.",
      );
    } finally {
      setLoading(false);
    }
  }

  function updateAssignment(
    sampleAccession: string,
    group: string,
  ) {
    setAssignments((current) =>
      current.map((item) =>
        item.sample_accession === sampleAccession
          ? { ...item, group }
          : item,
      ),
    );

    setAssignmentsReviewed(false);
    setDesignConfirmed(false);
    setApprovedPairs((current) =>
      current.map((pair) => ({ ...pair, approved: false })),
    );
    setExecution(null);
  }

  function updatePair(
    index: number,
    changes: Partial<GeoApprovedPair>,
  ) {
    setApprovedPairs((current) =>
      current.map((pair, pairIndex) =>
        pairIndex === index
          ? { ...pair, ...changes, approved: false }
          : pair,
      ),
    );
    setExecution(null);
  }

  function handleGroupChange(
    kind: "numerator" | "denominator",
    value: string,
  ) {
    if (kind === "numerator") {
      setNumeratorGroup(value);
    } else {
      setDenominatorGroup(value);
    }

    setDesignConfirmed(false);
    setApprovedPairs((current) =>
      current.map((pair) => ({ ...pair, approved: false })),
    );
    setExecution(null);
  }

  async function handleExecute() {
    if (!prepared || !canExecute) {
      setError(
        pairedAnalysis
          ? "Confirm the design and approve at least two valid, distinct patient pairs before execution."
          : "Complete the sample review and confirm the comparison and analysis settings before execution.",
      );
      return;
    }

    setLoading(true);
    setError("");
    setNotice("");
    setExecution(null);

    try {
      const result = await executeGeoAnalysis({
        accession: prepared.accession,
        assignments,
        numerator_group: numeratorGroup,
        denominator_group: denominatorGroup,
        assay_type: "processed_microarray",
        normalization_confirmed: normalizationConfirmed,
        design_confirmed: designConfirmed && assignmentsReviewed,
        paired_analysis: pairedAnalysis,
        approved_pairs: pairedAnalysis
          ? validPairs
          : [],
      });

      setExecution(result);
      setStage("results");
      setNotice(
        `Analysis status: ${result.analysis_status}. Results were returned by the backend.`,
      );
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Differential-expression analysis failed.",
      );
    } finally {
      setLoading(false);
    }
  }

  function downloadCsv() {
    if (!execution) return;

    const headers = [
      "gene_id",
      "direction",
      "contrast",
      "log2_fold_change",
      "average_expression",
      "moderated_t",
      "p_value",
      "adjusted_p_value",
      "B_statistic",
    ];

    const escapeCsv = (value: string | number) =>
      `"${String(value).replace(/"/g, '""')}"`;

    const content = [
      headers.join(","),
      ...resultRows.map((row) =>
        headers
          .map((header) =>
            escapeCsv(
              row[header as keyof GeoDifferentialExpressionRow],
            ),
          )
          .join(","),
      ),
    ].join("\r\n");

    const blob = new Blob([content], {
      type: "text/csv;charset=utf-8;",
    });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    link.href = url;
    link.download = `${execution.accession}_limma_results.csv`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  const tabs: {
    key: WorkflowStage;
    number: string;
    label: string;
    enabled: boolean;
    complete: boolean;
  }[] = [
    {
      key: "validation",
      number: "01",
      label: "Validate Matrix",
      enabled: true,
      complete: Boolean(validation),
    },
    {
      key: "design",
      number: "02",
      label: "Review Design",
      enabled: Boolean(prepared),
      complete: Boolean(prepared && assignmentsReviewed && designConfirmed),
    },
    {
      key: "pairing",
      number: "03",
      label: "Review Pairing",
      enabled: Boolean(prepared),
      complete: Boolean(
        pairedAnalysis &&
          approvedPairs.length >= 2 &&
          validPairs.length === approvedPairs.length,
      ),
    },
    {
      key: "results",
      number: "04",
      label: "Results",
      enabled: Boolean(execution),
      complete: Boolean(execution),
    },
  ];

  return (
    <main className="analysis-workspace">
      <header className="analysis-header">
        <div>
          <p className="analysis-kicker">
            RESEARCH WORKSPACE / ANALYSIS
          </p>
          <h1>Bioinformatics analysis</h1>
          <p className="analysis-muted">
            Validate a public GEO matrix, review its experimental
            design, and run differential expression using the
            configured limma engine.
          </p>
        </div>

        <span className="analysis-status">
          {execution?.analysis_status ??
            prepared?.analysis_status ??
            validation?.status ??
            "Awaiting dataset"}
        </span>
      </header>

      <nav
        className="analysis-steps analysis-workflow-tabs"
        aria-label="Analysis workflow tabs"
        role="tablist"
      >
        {tabs.map((tab) => (
          <button
            key={tab.key}
            type="button"
            role="tab"
            id={`analysis-tab-${tab.key}`}
            aria-selected={stage === tab.key}
            aria-controls={`analysis-panel-${tab.key}`}
            className={[
              "analysis-step",
              "analysis-tab-button",
              stage === tab.key ? "is-active" : "",
              tab.complete ? "is-complete" : "",
            ]
              .filter(Boolean)
              .join(" ")}
            disabled={!tab.enabled || loading}
            onClick={() => {
              setStage(tab.key);
              setError("");
              setNotice("");
            }}
          >
            <span>{tab.number}</span>
            <strong>{tab.label}</strong>
          </button>
        ))}
      </nav>

      {error && (
        <div
          className="analysis-message analysis-message-error"
          role="alert"
        >
          <strong>Action required</strong>
          <p>{error}</p>
        </div>
      )}

      {notice && (
        <div
          className="analysis-message analysis-message-info"
          role="status"
        >
          {notice}
        </div>
      )}

      {stage === "validation" && (
        <section
          className="analysis-panel"
          id="analysis-panel-validation"
          role="tabpanel"
          aria-labelledby="analysis-tab-validation"
        >
          <div className="analysis-panel-heading">
            <div>
              <p className="analysis-kicker">DATA SOURCE</p>
              <h2>Validate Matrix</h2>
            </div>
            <span className="analysis-muted">
              Processed microarray only
            </span>
          </div>

          <form
            className="analysis-accession-form"
            onSubmit={(event) => {
              event.preventDefault();
              void handleValidate();
            }}
          >
            <label htmlFor="geo-accession">
              GEO Series accession
            </label>
            <div className="analysis-input-row">
              <input
                id="geo-accession"
                value={accession}
                onChange={(event) =>
                  setAccession(event.target.value)
                }
                placeholder="e.g. GSE10072"
                autoComplete="off"
                spellCheck={false}
              />
              <button type="submit" disabled={loading}>
                {loading ? "Working…" : "Validate matrix"}
              </button>
            </div>
          </form>

          {validation && (
            <>
              <div className="analysis-metrics">
                <div className="analysis-metric">
                  <span>Matrix features</span>
                  <strong>
                    {validation.matrix_rows.toLocaleString()}
                  </strong>
                </div>
                <div className="analysis-metric">
                  <span>Matrix samples</span>
                  <strong>
                    {validation.matrix_columns.toLocaleString()}
                  </strong>
                </div>
                <div className="analysis-metric">
                  <span>Metadata samples</span>
                  <strong>
                    {validation.metadata_sample_count.toLocaleString()}
                  </strong>
                </div>
                <div className="analysis-metric">
                  <span>Assay type</span>
                  <strong>
                    {validation.assay_type || "Unknown"}
                  </strong>
                </div>
              </div>

              <p className="analysis-muted">
                Representation:{" "}
                {validation.data_representation || "Unknown"}.
                Sample IDs aligned:{" "}
                {validation.sample_ids_aligned ? "Yes" : "No"}.
              </p>

              {validation.warnings.length > 0 && (
                <div className="analysis-warning-list">
                  <strong>Validation warnings</strong>
                  <ul>
                    {validation.warnings.map((warning, index) => (
                      <li key={`${warning}-${index}`}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}

              {validation.errors.length > 0 && (
                <div className="analysis-warning-list is-error">
                  <strong>Validation errors</strong>
                  <ul>
                    {validation.errors.map((item, index) => (
                      <li key={`${item}-${index}`}>{item}</li>
                    ))}
                  </ul>
                </div>
              )}

              <button
                type="button"
                onClick={() => void handlePrepare()}
                disabled={
                  loading ||
                  !validation.ready_for_design_review ||
                  validation.errors.length > 0
                }
              >
                {loading
                  ? "Preparing…"
                  : "Prepare analysis and review samples"}
              </button>
            </>
          )}
        </section>
      )}

      {stage === "design" && prepared && (
        <section
          className="analysis-panel"
          id="analysis-panel-design"
          role="tabpanel"
          aria-labelledby="analysis-tab-design"
        >
          <div className="analysis-panel-heading">
            <div>
              <p className="analysis-kicker">RESEARCHER REVIEW</p>
              <h2>Review Design</h2>
            </div>
            <span className="analysis-muted">
              {assignments.length} samples
            </span>
          </div>

          <h3>{prepared.title}</h3>

          <p className="analysis-muted">
            Accession: {prepared.accession} · Matrix SHA-256:{" "}
            {prepared.provenance.sha256 || "Not supplied"} · Cache hit:{" "}
            {prepared.provenance.cache_hit ? "Yes" : "No"}
          </p>

          <div className="analysis-table-wrap">
            <table className="analysis-table">
              <thead>
                <tr>
                  <th>Sample</th>
                  <th>Suggested group</th>
                  <th>Evidence</th>
                  <th>Confirmed group</th>
                </tr>
              </thead>
              <tbody>
                {prepared.design_review.group_assignments.map((sample) => {
                  const assignment = assignments.find(
                    (item) =>
                      item.sample_accession === sample.sample_accession,
                  );

                  return (
                    <tr key={sample.sample_accession}>
                      <td>{sample.sample_accession}</td>
                      <td>
                        {sample.suggested_group ?? "Unclassified"}
                      </td>
                      <td>
                        {sample.group_evidence.length
                          ? sample.group_evidence.join("; ")
                          : "No evidence supplied"}
                      </td>
                      <td>
                        <select
                          aria-label={`Confirmed group for ${sample.sample_accession}`}
                          value={assignment?.group ?? ""}
                          onChange={(event) =>
                            updateAssignment(
                              sample.sample_accession,
                              event.target.value,
                            )
                          }
                        >
                          <option value="">Select group</option>
                          {[
                            ...new Set([
                              ...prepared.design_review.suggested_groups.map(
                                (group) => group.name,
                              ),
                              ...groupNames,
                            ]),
                          ]
                            .filter(Boolean)
                            .map((group) => (
                              <option key={group} value={group}>
                                {group}
                              </option>
                            ))}
                        </select>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {prepared.design_review.warnings.length > 0 && (
            <div className="analysis-warning-list">
              <strong>Design review warnings</strong>
              <ul>
                {prepared.design_review.warnings.map((warning, index) => (
                  <li key={`${warning}-${index}`}>{warning}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="analysis-design-grid">
            <div>
              <label htmlFor="numerator-group">
                Numerator group
              </label>
              <select
                id="numerator-group"
                value={numeratorGroup}
                onChange={(event) =>
                  handleGroupChange("numerator", event.target.value)
                }
              >
                <option value="">Select numerator</option>
                {groupNames.map((group) => (
                  <option key={group} value={group}>
                    {group}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label htmlFor="denominator-group">
                Denominator group
              </label>
              <select
                id="denominator-group"
                value={denominatorGroup}
                onChange={(event) =>
                  handleGroupChange("denominator", event.target.value)
                }
              >
                <option value="">Select denominator</option>
                {groupNames.map((group) => (
                  <option key={group} value={group}>
                    {group}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {numeratorGroup &&
            denominatorGroup &&
            numeratorGroup === denominatorGroup && (
              <p className="analysis-inline-error">
                Choose two different groups for the comparison.
              </p>
            )}

          {assignedCount !== assignments.length && (
            <p className="analysis-inline-error">
              Assign a group to every sample before execution.
            </p>
          )}

          <div className="analysis-confirmations">
            <label>
              <input
                type="checkbox"
                checked={assignmentsReviewed}
                onChange={(event) => {
                  setAssignmentsReviewed(event.target.checked);
                  setDesignConfirmed(false);
                  setApprovedPairs((current) =>
                    current.map((pair) => ({
                      ...pair,
                      approved: false,
                    })),
                  );
                }}
              />
              I reviewed and confirmed the group assignment for every sample.
            </label>

            <label>
              <input
                type="checkbox"
                checked={normalizationConfirmed}
                onChange={(event) =>
                  setNormalizationConfirmed(event.target.checked)
                }
              />
              I reviewed the processed microarray values and confirm the
              analysis assumptions are appropriate.
            </label>

            <label>
              <input
                type="checkbox"
                checked={designConfirmed}
                onChange={(event) =>
                  setDesignConfirmed(event.target.checked)
                }
              />
              I confirm the comparison design and selected group direction.
            </label>
          </div>

          <div className="analysis-confirmations">
            <label>
              <input
                type="checkbox"
                checked={pairedAnalysis}
                onChange={(event) => {
                  setPairedAnalysis(event.target.checked);
                  setApprovedPairs([]);
                  setExecution(null);
                }}
              />
              Use paired analysis for verified tumour–normal samples.
            </label>
            <p className="analysis-muted">
              Leave this unchecked for the existing unpaired workflow.
              Enable it only when samples have defensible patient-level
              pairing evidence.
            </p>
          </div>

          <div className="analysis-action-row">
            <button
              type="button"
              className="analysis-button-secondary"
              onClick={() => {
                setAssignments(
                  prepared.design_review.group_assignments.map((sample) => ({
                    sample_accession: sample.sample_accession,
                    group: "",
                  })),
                );
                setAssignmentsReviewed(false);
                setDesignConfirmed(false);
                setApprovedPairs([]);
                setExecution(null);
              }}
              disabled={loading}
            >
              Clear assignments
            </button>

            {pairedAnalysis ? (
              <button
                type="button"
                onClick={() => {
                  setError("");
                  setNotice("");
                  setStage("pairing");
                }}
                disabled={
                  loading ||
                  !assignmentsReviewed ||
                  !designConfirmed ||
                  !normalizationConfirmed ||
                  !numeratorGroup ||
                  !denominatorGroup ||
                  numeratorGroup === denominatorGroup ||
                  assignedCount !== assignments.length
                }
              >
                Review Pairing
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void handleExecute()}
                disabled={!canExecute}
              >
                {loading ? "Running limma…" : "Confirm and run limma"}
              </button>
            )}
          </div>
        </section>
      )}

      {stage === "pairing" && prepared && (
        <section
          className="analysis-panel"
          id="analysis-panel-pairing"
          role="tabpanel"
          aria-labelledby="analysis-tab-pairing"
        >
          <div className="analysis-panel-heading">
            <div>
              <p className="analysis-kicker">PAIRED DESIGN REVIEW</p>
              <h2>Review Pairing</h2>
            </div>
            <span className="analysis-muted">
              {validPairs.length} approved pairs
            </span>
          </div>

          <p className="analysis-muted">
            Dataset: {prepared.accession} · Numerator: {numeratorGroup} ·
            Denominator: {denominatorGroup}
          </p>

          <div className="analysis-warning-list">
            <strong>Evidence and approval requirements</strong>
            <ul>
              <li>
                Match samples from the same patient only when supported
                by study metadata or other reliable evidence.
              </li>
              <li>
                Enter the study's patient identifier; do not invent IDs
                or pair samples based only on their group labels.
              </li>
              <li>
                Each patient and sample can appear in at most one pair.
              </li>
              <li>
                Researcher approval records your proposed mapping. The
                backend must independently verify GEO evidence before
                accepting paired analysis.
              </li>
            </ul>
          </div>

          {prepared.design_review.pairing_candidates.length > 0 && (
            <p className="analysis-muted">
              The preparation step returned{" "}
              {prepared.design_review.pairing_candidates.length} pairing
              candidate record(s). Review the study metadata before
              entering and approving a pair below.
            </p>
          )}

          {approvedPairs.map((pair, index) => (
            <div className="analysis-pair-card" key={`pair-${index}`}>
              <div className="analysis-panel-heading">
                <h3>Pair {index + 1}</h3>
                <button
                  type="button"
                  className="analysis-button-secondary"
                  onClick={() => {
                    setApprovedPairs((current) =>
                      current.filter((_, itemIndex) => itemIndex !== index),
                    );
                    setExecution(null);
                  }}
                  disabled={loading}
                >
                  Remove
                </button>
              </div>

              <div className="analysis-design-grid">
                <div>
                  <label htmlFor={`pair-tumour-${index}`}>
                    Tumour / numerator sample
                  </label>
                  <select
                    id={`pair-tumour-${index}`}
                    value={pair.tumour_accession}
                    onChange={(event) =>
                      updatePair(index, {
                        tumour_accession: event.target.value,
                      })
                    }
                  >
                    <option value="">Select sample</option>
                    {assignments
                      .filter(
                        (item) => item.group === numeratorGroup,
                      )
                      .map((item) => (
                        <option
                          key={item.sample_accession}
                          value={item.sample_accession}
                        >
                          {item.sample_accession}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label htmlFor={`pair-normal-${index}`}>
                    Normal / denominator sample
                  </label>
                  <select
                    id={`pair-normal-${index}`}
                    value={pair.normal_accession}
                    onChange={(event) =>
                      updatePair(index, {
                        normal_accession: event.target.value,
                      })
                    }
                  >
                    <option value="">Select sample</option>
                    {assignments
                      .filter(
                        (item) => item.group === denominatorGroup,
                      )
                      .map((item) => (
                        <option
                          key={item.sample_accession}
                          value={item.sample_accession}
                        >
                          {item.sample_accession}
                        </option>
                      ))}
                  </select>
                </div>

                <div>
                  <label htmlFor={`pair-patient-${index}`}>
                    Patient identifier from study evidence
                  </label>
                  <input
                    id={`pair-patient-${index}`}
                    value={pair.patient_id}
                    onChange={(event) =>
                      updatePair(index, {
                        patient_id: event.target.value,
                      })
                    }
                    placeholder="Study patient ID"
                    autoComplete="off"
                  />
                </div>
              </div>

              <div className="analysis-confirmations">
                <label>
                  <input
                    type="checkbox"
                    checked={pair.approved}
                    disabled={
                      !pair.tumour_accession ||
                      !pair.normal_accession ||
                      !pair.patient_id.trim() ||
                      pair.tumour_accession === pair.normal_accession ||
                      loading
                    }
                    onChange={(event) =>
                      setApprovedPairs((current) =>
                        current.map((item, itemIndex) =>
                          itemIndex === index
                            ? {
                                ...item,
                                approved: event.target.checked,
                              }
                            : item,
                        ),
                      )
                    }
                  />
                  I reviewed the study evidence and approve this
                  tumour–normal patient pairing.
                </label>
              </div>
            </div>
          ))}

          <div className="analysis-action-row">
            <button
              type="button"
              className="analysis-button-secondary"
              onClick={() => {
                setStage("design");
                setError("");
                setNotice("");
              }}
            >
              Back to Review Design
            </button>

            <button
              type="button"
              className="analysis-button-secondary"
              onClick={() =>
                setApprovedPairs((current) => [
                  ...current,
                  {
                    tumour_accession: "",
                    normal_accession: "",
                    patient_id: "",
                    approved: false,
                  },
                ])
              }
              disabled={loading}
            >
              Add pair
            </button>

            <button
              type="button"
              onClick={() => void handleExecute()}
              disabled={!canExecute}
            >
              {loading
                ? "Verifying pairs and running limma…"
                : "Verify pairs and run paired limma"}
            </button>
          </div>

          {pairedAnalysis &&
            approvedPairs.length > 0 &&
            validPairs.length !== approvedPairs.length && (
              <p className="analysis-inline-error">
                Review all pairs. At least two approved pairs are required;
                samples and patient IDs must be unique, and the groups must
                match the selected comparison.
              </p>
            )}
        </section>
      )}

      {stage === "results" && execution && (
        <section
          className="analysis-results"
          id="analysis-panel-results"
          role="tabpanel"
          aria-labelledby="analysis-tab-results"
        >
          <div className="analysis-panel">
            <div className="analysis-panel-heading">
              <div>
                <p className="analysis-kicker">COMPLETED ANALYSIS</p>
                <h2>Differential expression</h2>
              </div>
              <button
                type="button"
                className="analysis-button-secondary"
                onClick={downloadCsv}
              >
                Export CSV
              </button>
            </div>

            <p className="analysis-muted">
              {execution.accession} · {execution.analysis_method} ·{" "}
              {execution.assay_type}
            </p>

            <p>
              Comparison:{" "}
              <strong>{execution.comparison.numerator_group}</strong>
              {" versus "}
              <strong>{execution.comparison.denominator_group}</strong>
            </p>

            <p className="analysis-muted">
              Design: {pairedAnalysis ? "Paired" : "Unpaired"}
              {pairedAnalysis
                ? ` · ${validPairs.length} approved patient pairs`
                : ""}
            </p>

            {execution.comparison.direction_explanation && (
              <p className="analysis-muted">
                {execution.comparison.direction_explanation}
              </p>
            )}

            <div className="analysis-metrics">
              <div className="analysis-metric">
                <span>Features tested</span>
                <strong>
                  {execution.results.features_tested.toLocaleString()}
                </strong>
              </div>
              <div className="analysis-metric">
                <span>Significant features</span>
                <strong>{significantRows.length.toLocaleString()}</strong>
              </div>
              <div className="analysis-metric">
                <span>Positive log2FC</span>
                <strong>{positiveCount.toLocaleString()}</strong>
              </div>
              <div className="analysis-metric">
                <span>Negative log2FC</span>
                <strong>{negativeCount.toLocaleString()}</strong>
              </div>
            </div>

            <p className="analysis-muted">
              Significance threshold: adjusted p-value &lt;{" "}
              {significanceThreshold}. Counts represent tested features
              or probes returned by the backend, not necessarily unique genes.
            </p>
          </div>

          <div className="analysis-panel">
            <div className="analysis-panel-heading">
              <div>
                <p className="analysis-kicker">EXPRESSION STATISTICS</p>
                <h2>Volcano plot</h2>
              </div>
            </div>

            <VolcanoPlot
              rows={resultRows}
              threshold={significanceThreshold}
            />
          </div>

          <div className="analysis-panel">
            <div className="analysis-panel-heading">
              <div>
                <p className="analysis-kicker">FEATURE-LEVEL RESULTS</p>
                <h2>Statistical results</h2>
              </div>
              <span className="analysis-muted">
                {visibleRows.length.toLocaleString()} rows
              </span>
            </div>

            <div className="analysis-filter-row">
              <label htmlFor="result-filter">Show</label>
              <select
                id="result-filter"
                value={filter}
                onChange={(event) =>
                  setFilter(event.target.value as ResultFilter)
                }
              >
                <option value="all">All features</option>
                <option value="significant">Significant only</option>
                <option value="positive">
                  Significant positive log2FC
                </option>
                <option value="negative">
                  Significant negative log2FC
                </option>
              </select>
            </div>

            <div className="analysis-table-wrap">
              <table className="analysis-table">
                <thead>
                  <tr>
                    <th>Feature / gene ID</th>
                    <th>Direction</th>
                    <th>log2FC</th>
                    <th>Average expression</th>
                    <th>Moderated t</th>
                    <th>p-value</th>
                    <th>Adjusted p-value</th>
                    <th>B-statistic</th>
                  </tr>
                </thead>
                <tbody>
                  {visibleRows.slice(0, 200).map((row, index) => (
                    <tr key={`${row.gene_id}-${index}`}>
                      <td>{row.gene_id}</td>
                      <td>{row.direction}</td>
                      <td>{formatNumber(row.log2_fold_change)}</td>
                      <td>{formatNumber(row.average_expression)}</td>
                      <td>{formatNumber(row.moderated_t)}</td>
                      <td>{formatPValue(row.p_value)}</td>
                      <td>{formatPValue(row.adjusted_p_value)}</td>
                      <td>{formatNumber(row.B_statistic)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {visibleRows.length > 200 && (
              <p className="analysis-muted">
                Showing the first 200 rows sorted by adjusted p-value.
                Export CSV to access all{" "}
                {visibleRows.length.toLocaleString()} matching rows.
              </p>
            )}

            {visibleRows.length === 0 && (
              <p className="analysis-muted">
                No features match the selected filter.
              </p>
            )}
          </div>
        </section>
      )}
    </main>
  );
}
