import type { NavItem } from "../types/navigation";

export const primaryNav: NavItem[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    path: "/",
    icon: "home",
    title: "Dashboard",
    description: "Overview of BioNexus Omni research workspaces.",
  },
  {
    id: "research",
    label: "New Research",
    path: "/research",
    icon: "plus",
    title: "New Research",
    description: "Start a research investigation from a biological question.",
  },
  {
    id: "datasets",
    label: "Dataset Discovery",
    path: "/datasets",
    icon: "database",
    title: "Dataset Discovery",
    description: "Search and evaluate NCBI/SRA studies before analysis.",
  },
  {
    id: "genes",
    label: "Gene Research",
    path: "/genes",
    icon: "gene",
    title: "Gene Research",
    description: "Inspect gene-centered evidence once research jobs exist.",
  },
  {
    id: "analysis",
    label: "Analysis",
    path: "/analysis",
    icon: "analysis",
    title: "Analysis",
    description: "Review bioinformatics analysis outputs when they are available.",
  },
  {
    id: "pathways",
    label: "Pathways & Networks",
    path: "/pathways",
    icon: "pathways",
    title: "Pathways & Networks",
    description: "Explore pathway and network results from completed analyses.",
  },
  {
    id: "visualizations",
    label: "Visualizations",
    path: "/visualizations",
    icon: "visualizations",
    title: "Visualizations",
    description: "View figures generated from connected research jobs.",
  },
  {
    id: "literature",
    label: "Literature",
    path: "/literature",
    icon: "literature",
    title: "Literature",
    description: "Collect literature evidence attached to a research job.",
  },
  {
    id: "reports",
    label: "Reports",
    path: "/reports",
    icon: "reports",
    title: "Reports",
    description: "Open scientific reports produced by the research workflow.",
  },
  {
    id: "knowledge",
    label: "Knowledge",
    path: "/knowledge",
    icon: "knowledge",
    title: "Knowledge",
    description: "Browse retained findings once a knowledge store exists.",
  },
];

export const settingsNav: NavItem = {
  id: "settings",
  label: "Settings",
  path: "/settings",
  icon: "settings",
  title: "Settings",
  description: "Configure Omni workspace preferences.",
};

export const allNavItems: NavItem[] = [...primaryNav, settingsNav];

export function navItemForPath(pathname: string): NavItem {
  const exact = allNavItems.find((item) => item.path === pathname);
  if (exact) {
    return exact;
  }

  return primaryNav[0];
}
