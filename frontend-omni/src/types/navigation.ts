export type AppRouteId =
  | "dashboard"
  | "research"
  | "datasets"
  | "genes"
  | "analysis"
  | "pathways"
  | "visualizations"
  | "literature"
  | "reports"
  | "knowledge"
  | "settings";

export type IconName =
  | "home"
  | "plus"
  | "database"
  | "gene"
  | "analysis"
  | "pathways"
  | "visualizations"
  | "literature"
  | "reports"
  | "knowledge"
  | "settings"
  | "search"
  | "bell"
  | "sun"
  | "moon"
  | "menu"
  | "close"
  | "assistant"
  | "arrow";

export interface NavItem {
  id: AppRouteId;
  label: string;
  path: string;
  icon: IconName;
  title: string;
  description: string;
}
