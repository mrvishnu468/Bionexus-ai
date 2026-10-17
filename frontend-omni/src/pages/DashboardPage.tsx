import { Button } from "../components/Button";
import { Card } from "../components/Card";
import { EmptyState } from "../components/EmptyState";
import { Icon } from "../components/Icon";
import { StatusBadge } from "../components/StatusBadge";

export function DashboardPage() {
  return (
    <div className="page-stack">
      <section className="welcome-panel">
        <p className="page-kicker">BioNexus Omni</p>
        <h2>Evidence-grounded research workspace</h2>
        <p>
          Start from a biological question, evaluate public sequencing studies,
          and keep later analysis, literature, and reports in one place. This
          foundation is not connected to the research engine yet.
        </p>
        <div className="welcome-actions">
          <Button to="/research" icon={<Icon name="plus" />}>
            New research
          </Button>
          <Button to="/datasets" variant="secondary" icon={<Icon name="database" />}>
            Dataset discovery
          </Button>
        </div>
      </section>

      <div className="dashboard-grid">
        <Card>
          <div className="card-heading">
            <h3>Recent projects</h3>
            <StatusBadge label="No jobs stored" />
          </div>
          <EmptyState title="No research projects yet">
            Project history will appear here after research jobs are created
            and persisted. Nothing is invented for this view.
          </EmptyState>
        </Card>

        <Card>
          <div className="card-heading">
            <h3>Research activity</h3>
            <StatusBadge label="Unavailable" />
          </div>
          <EmptyState title="No activity to show">
            Status changes, dataset searches, and workflow stages will list
            here once the API client is connected.
          </EmptyState>
        </Card>
      </div>

      <div className="dashboard-grid">
        <Card>
          <div className="card-heading">
            <h3>Dataset discovery</h3>
          </div>
          <p className="card-copy">
            Search NCBI/SRA and review study suitability before analysis. Search
            is not wired in this milestone.
          </p>
          <Button to="/datasets" variant="secondary">
            Open dataset discovery
          </Button>
        </Card>

        <Card>
          <div className="card-heading">
            <h3>Research system</h3>
            <StatusBadge label="Not connected" />
          </div>
          <p className="card-copy">
            Engine health, job queue, and NCBI reachability are not queried
            yet. Status is unavailable rather than assumed ready.
          </p>
        </Card>
      </div>
    </div>
  );
}
