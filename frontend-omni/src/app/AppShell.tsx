
import { useEffect, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { AssistantPanel } from "./AssistantPanel";
import { Header } from "./Header";
import { Sidebar } from "./Sidebar";
import { navItemForPath } from "./navigation";

type Theme = "dark" | "light";

function getInitialTheme(): Theme {
  try {
    return localStorage.getItem("bionexus-theme") === "light"
      ? "light"
      : "dark";
  } catch {
    return "dark";
  }
}

export function AppShell() {
  const location = useLocation();
  const current = navItemForPath(location.pathname);
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [assistantOpen, setAssistantOpen] = useState(false);
  const [theme, setTheme] = useState<Theme>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try {
      localStorage.setItem("bionexus-theme", theme);
    } catch {
      // Theme still works for the current session if storage is unavailable.
    }
  }, [theme]);

  useEffect(() => {
    setSidebarOpen(false);
  }, [location.pathname]);

  return (
    <div className="app-shell">
      <Sidebar
        open={sidebarOpen}
        onNavigate={() => setSidebarOpen(false)}
        onOpenAssistant={() => setAssistantOpen(true)}
      />

      {sidebarOpen ? (
        <button
          type="button"
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      ) : null}

      <div className="app-main">
        <Header
          title={current.title}
          sidebarOpen={sidebarOpen}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          theme={theme}
          onToggleTheme={() =>
            setTheme((currentTheme) =>
              currentTheme === "dark" ? "light" : "dark",
            )
          }
        />
        <main className="page-content">
          <Outlet />
        </main>
      </div>

      <AssistantPanel
        open={assistantOpen}
        onClose={() => setAssistantOpen(false)}
      />
    </div>
  );
}
