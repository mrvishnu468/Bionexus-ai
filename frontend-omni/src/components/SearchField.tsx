interface SearchFieldProps {
  placeholder: string;
  label: string;
}

export function SearchField({ placeholder, label }: SearchFieldProps) {
  return (
    <label className="global-search">
      <span className="sr-only">{label}</span>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <path
          d="M11 18a7 7 0 1 1 0-14 7 7 0 0 1 0 14zm6.5-1.5 3.5 3.5"
          stroke="currentColor"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
      <input type="search" placeholder={placeholder} disabled />
      <kbd>Ctrl</kbd>
      <kbd>K</kbd>
    </label>
  );
}
