import type { ReactNode } from "react";

// Minimal line glyphs (white stroke on the black taxonomy blocks).
const ICONS: Record<string, ReactNode> = {
  budget: (
    <>
      <circle cx="12" cy="12" r="8" />
      <path d="M12 7.5v9M14.2 9.4c-.4-.8-1.3-1.2-2.2-1.2-1.2 0-2.2.7-2.2 1.8 0 2.4 4.6 1.2 4.6 3.7 0 1.1-1 1.9-2.4 1.9-1 0-1.9-.4-2.3-1.2" />
    </>
  ),
  fees: (
    <>
      <path d="M6 4h12v16l-2-1.3-2 1.3-2-1.3-2 1.3-2-1.3L6 20z" />
      <path d="M9 8.5h6M9 12h6M9 15.5h3" />
    </>
  ),
  recurring: (
    <>
      <path d="M5 12a7 7 0 0 1 11.5-5.3M19 12a7 7 0 0 1-11.5 5.3" />
      <path d="M16.5 4v3h-3M7.5 20v-3h3" />
    </>
  ),
  merchant: (
    <>
      <path d="M4 9l1.4-4h13.2L20 9" />
      <path d="M4 9c0 1.4 1 2.4 2.2 2.4S8.5 10.4 8.5 9c0 1.4 1 2.4 2.2 2.4S13 10.4 13 9c0 1.4 1 2.4 2.2 2.4S17.5 10.4 17.5 9" />
      <path d="M5.5 11.4V20h13v-8.6M9.5 20v-5h5v5" />
    </>
  ),
  category: (
    <>
      <path d="M4 12.5V5h7.5L20 13.5 13.5 20 4 12.5z" />
      <circle cx="8" cy="9" r="1.2" />
    </>
  ),
  approval: (
    <>
      <path d="M12 3l7 2.5v5.5c0 4.3-2.9 7.5-7 9-4.1-1.5-7-4.7-7-9V5.5z" />
      <path d="M9 12l2 2 4-4" />
    </>
  ),
  evasion: (
    <>
      <path d="M4 8h6l4 8h6M4 16h6l1.5-3M16.5 5l3 3-3 3M16.5 13l3 3-3 3" />
    </>
  ),
  privacy: (
    <>
      <path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z" />
      <circle cx="12" cy="12" r="3" />
      <path d="M4 4l16 16" />
    </>
  ),
  injection: (
    <>
      <rect x="4" y="6" width="16" height="12" rx="2" />
      <path d="M8 10l-2 2 2 2M16 10l2 2-2 2M13 9.5l-2 5" />
    </>
  ),
  settlement: (
    <>
      <path d="M3 8h5l3 3M21 8h-5l-3 3" />
      <path d="M8 11l2.5 2.5a1.6 1.6 0 0 0 2.3 0L16 11" />
      <path d="M3 8v6h2M21 8v6h-2" />
    </>
  ),
  welfare: (
    <>
      <path d="M12 20S4 14.7 4 9.3C4 6.6 6 5 8.2 5c1.6 0 2.9.9 3.8 2.2C12.9 5.9 14.2 5 15.8 5 18 5 20 6.6 20 9.3c0 5.4-8 10.7-8 10.7z" />
    </>
  ),
  audit: (
    <>
      <rect x="6" y="4" width="12" height="16" rx="1.5" />
      <path d="M9 3.5h6V6H9zM9 10h6M9 13.5h6M9 17h4" />
    </>
  ),
};

export function Icon({
  name,
  className,
}: {
  name: string;
  className?: string;
}) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.5}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {ICONS[name] ?? <circle cx="12" cy="12" r="7" />}
    </svg>
  );
}
