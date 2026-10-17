import { PageHeader } from "../components/PageHeader";
import { StatusBadge } from "../components/StatusBadge";
import { API_BASE_URL, apiRoutes } from "../services/api";

export function SettingsPage() {
  return (
    <div className="page-stack">
      <PageHeader
        kicker="Workspace"
        title="Settings"
        description="Reserved configuration for the Omni client. Values are shown for later integration and are not applied to live requests yet."
      />

      <section className="settings-list">
        <div className="settings-row">
          <div>
            <h3>API base URL</h3>
            <p>Existing FastAPI origin reserved for typed clients.</p>
          </div>
          <code>{API_BASE_URL}</code>
        </div>
        <div className="settings-row">
          <div>
            <h3>Health endpoint</h3>
            <p>Not queried in this milestone.</p>
          </div>
          <code>{apiRoutes.health}</code>
        </div>
        <div className="settings-row">
          <div>
            <h3>Connection</h3>
            <p>No request is sent, so health is not inferred.</p>
          </div>
          <StatusBadge label="Not connected" />
        </div>
      </section>
    </div>
  );
}
