import { NavLink } from "react-router-dom";
import { Icon } from "../components/Icon";
import { primaryNav, settingsNav } from "./navigation";

interface SidebarProps {
  open: boolean;
  onNavigate: () => void;
  onOpenAssistant: () => void;
}

export function Sidebar({ open, onNavigate, onOpenAssistant }: SidebarProps) {
  return (
    <aside className={`app-sidebar ${open ? "is-open" : ""}`} id="app-sidebar">
      <div className="brand">
        <div className="brand-mark" aria-hidden="true">
          B
        </div>
        <div className="brand-copy">
          <strong>BioNexus Omni</strong>
          <span>AI research workspace</span>
        </div>
      </div>

      <nav className="sidebar-nav" aria-label="Primary">
        {primaryNav.map((item) => (
          <NavLink
            key={item.id}
            to={item.path}
            end={item.path === "/"}
            className={({ isActive }) =>
              `nav-item${isActive ? " is-active" : ""}`
            }
            onClick={onNavigate}
          >
            <span className="nav-icon">
              <Icon name={item.icon} />
            </span>
            <span>{item.label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-bottom">
        <button
          type="button"
          className="assistant-entry"
          onClick={onOpenAssistant}
        >
          <span className="nav-icon">
            <Icon name="assistant" />
          </span>
          <span className="assistant-entry-copy">
            <strong>AI assistant</strong>
            <em>Not connected</em>
          </span>
        </button>

        <NavLink
          to={settingsNav.path}
          className={({ isActive }) =>
            `nav-item${isActive ? " is-active" : ""}`
          }
          onClick={onNavigate}
        >
          <span className="nav-icon">
            <Icon name={settingsNav.icon} />
          </span>
          <span>{settingsNav.label}</span>
        </NavLink>
      </div>
    </aside>
  );
}
