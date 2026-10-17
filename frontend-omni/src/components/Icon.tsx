import type { IconName } from "../types/navigation";

interface IconProps {
  name: IconName;
  size?: number;
}

const paths: Record<IconName, string> = {
  home: "M4 10.5 12 4l8 6.5V20a1 1 0 0 1-1 1h-5v-6H10v6H5a1 1 0 0 1-1-1z",
  plus: "M12 5v14M5 12h14",
  database:
    "M5 7c0 1.7 3.1 3 7 3s7-1.3 7-3-3.1-3-7-3-7 1.3-7 3zm0 5c0 1.7 3.1 3 7 3s7-1.3 7-3M5 17c0 1.7 3.1 3 7 3s7-1.3 7-3",
  gene: "M5 8c3-4 11-4 14 0M5 16c3 4 11 4 14 0M8 12h8",
  analysis: "M5 19V9m5 10V5m5 14v-7m5 7V8",
  pathways: "M7 7h4v4H7zM13 13h4v4h-4zM9 11l6 2M8 7C5 9 5 15 8 17",
  visualizations: "M4 19h16M7 16l3-5 3 3 4-7",
  literature: "M6 5h9a3 3 0 0 1 3 3v11H8a2 2 0 0 0-2 2V5zm0 0v13",
  reports: "M7 4h8l4 4v12H7zM15 4v4h4M9 13h6M9 17h4",
  knowledge: "M5 6h6a3 3 0 0 1 3 3v11H8a3 3 0 0 0-3 3V6zm8 0h6v14a3 3 0 0 0-3-3h-3",
  settings:
    "M12 8.5a3.5 3.5 0 1 1 0 7 3.5 3.5 0 0 1 0-7zM12 3v2.2M12 18.8V21M21 12h-2.2M5.2 12H3M18.4 5.6l-1.6 1.6M7.2 16.8l-1.6 1.6M18.4 18.4l-1.6-1.6M7.2 7.2 5.6 5.6",
  search: "M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm6.5-1.5 3.5 3.5",
  bell: "M12 22a2 2 0 0 0 2-2H10a2 2 0 0 0 2 2zm6-6V11a6 6 0 1 0-12 0v5l-2 2h16z",
  sun: "M12 3v2m0 14v2M3 12h2m14 0h2M5.64 5.64l1.42 1.42m9.88 9.88 1.42 1.42m0-12.72-1.42 1.42m-9.88 9.88-1.42 1.42M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0z",
  moon: "M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5 8.5 8.5 0 1 0 20.5 14.5z",
  menu: "M5 7h14M5 12h14M5 17h14",
  close: "M7 7l10 10M17 7 7 17",
  assistant: "M8 10h.01M16 10h.01M8.5 15c1.2 1 5.8 1 7 0M6 7h12l2 6v5a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2v-5z",
  arrow: "M5 12h14M13 6l6 6-6 6",
};

export function Icon({ name, size = 18 }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden="true"
    >
      <path
        d={paths[name]}
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
