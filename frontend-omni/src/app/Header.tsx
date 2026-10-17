
import { Icon } from "../components/Icon";
import { SearchField } from "../components/SearchField";

interface HeaderProps {
  title: string;
  onToggleSidebar: () => void;
  sidebarOpen: boolean;
  theme: "dark" | "light";
  onToggleTheme: () => void;
}

export function Header({
  title,
  onToggleSidebar,
  sidebarOpen,
  theme,
  onToggleTheme,
}: HeaderProps) {
  const nextTheme = theme === "dark" ? "light" : "dark";

  return (
    <header className="app-header">
      <div className="header-start">
        <button
          type="button"
          className="icon-button sidebar-toggle"
          aria-label={sidebarOpen ? "Close navigation" : "Open navigation"}
          aria-expanded={sidebarOpen}
          aria-controls="app-sidebar"
          onClick={onToggleSidebar}
        >
          <Icon name={sidebarOpen ? "close" : "menu"} />
        </button>
        <h1 className="header-title">{title}</h1>
      </div>

      <div className="header-actions">
        <SearchField
          label="Global search"
          placeholder="Search datasets, genes, pathways, or research"
        />
        <button
          type="button"
          className="icon-button"
          aria-label={`Switch to ${nextTheme} theme`}
          title={`Switch to ${nextTheme} theme`}
          onClick={onToggleTheme}
        >
          <Icon name={theme === "dark" ? "sun" : "moon"} />
        </button>
      </div>
    </header>
  );
}
