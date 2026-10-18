import React from "react";
import "./App.css";
import {
  BarChart3,
  Bell,
  BookOpen,
  Database,
  FileText,
  Home as HomeIcon,
  LayoutDashboard,
  Plus,
  Search,
  Settings,
  Waves,
} from "lucide-react";

import Home from "./pages/Home";
import Datasets from "./pages/Datasets";

type Page =
  | "home"
  | "research"
  | "datasets"
  | "analysis"
  | "visualization"
  | "reports"
  | "knowledge"
  | "settings";

type NavItem = {
  id: Page;
  label: string;
  icon: typeof HomeIcon;
};

const navItems: NavItem[] = [
  {
    id: "home",
    label: "Home",
    icon: HomeIcon,
  },
  {
    id: "research",
    label: "New Research",
    icon: Plus,
  },
  {
    id: "datasets",
    label: "Datasets",
    icon: Database,
  },
  {
    id: "analysis",
    label: "Analysis",
    icon: BarChart3,
  },
  {
    id: "visualization",
    label: "Visualization",
    icon: Waves,
  },
  {
    id: "reports",
    label: "Reports",
    icon: FileText,
  },
  {
    id: "knowledge",
    label: "Knowledge",
    icon: BookOpen,
  },
];

function App() {
  const [page, setPage] = React.useState<Page>("home");

  function renderPage() {
    switch (page) {
      case "home":
        return <Home />;

      case "datasets":
        return <Datasets />;

      case "research":
        return <Home />;

      default:
        return (
          <div className="placeholder-page">
            <div className="placeholder-icon">
              <LayoutDashboard size={24} />
            </div>

            <p className="eyebrow">BI NEXUS WORKSPACE</p>

            <h1>
              {page.charAt(0).toUpperCase() + page.slice(1)}
            </h1>

            <p>
              This workspace is being connected to the BioNexus
              research engine.
            </p>
          </div>
        );
    }
  }

  return (
    <div className="app-shell">
      <aside className="app-sidebar">
        <div className="brand">
          <div className="brand-mark">
            <span>B</span>
          </div>

          <div className="brand-copy">
            <strong>BioNexus</strong>
            <span>AI Research Assistant</span>
          </div>
        </div>

        <nav className="sidebar-nav">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active =
              page === item.id ||
              (item.id === "research" && page === "research");

            return (
              <button
                key={item.id}
                className={`nav-item ${
                  active ? "active" : ""
                }`}
                onClick={() => setPage(item.id)}
              >
                <span className="nav-icon">
                  <Icon size={20} strokeWidth={1.8} />
                </span>

                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-bottom">
          <button
            className={`nav-item ${
              page === "settings" ? "active" : ""
            }`}
            onClick={() => setPage("settings")}
          >
            <span className="nav-icon">
              <Settings size={20} strokeWidth={1.8} />
            </span>

            <span>Settings</span>
          </button>

          <div className="engine-status">
            <span className="status-dot" />
            <span>Research engine ready</span>
          </div>
        </div>
      </aside>

      <main className="app-main">
        <header className="topbar">
          <div className="global-search">
            <Search size={19} strokeWidth={1.8} />

            <span>
              Search datasets, genes, pathways, or research...
            </span>

            <kbd>Ctrl</kbd>
            <kbd>K</kbd>
          </div>

          <div className="topbar-actions">
            <button className="icon-button" aria-label="Notifications">
              <Bell size={19} strokeWidth={1.8} />
              <span className="notification-dot" />
            </button>

            <div className="profile">
              <div className="profile-avatar">V</div>

              <span>Vishnu</span>

              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
              >
                <path
                  d="m6 9 6 6 6-6"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
              </svg>
            </div>
          </div>
        </header>

        <section className="page-content">
          {renderPage()}
        </section>
      </main>
    </div>
  );
}

export default App;