"use client";

export function AppLogo({ className = "h-7 w-7" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 108 108"
      className={`${className} shrink-0 rounded-[4px]`}
      aria-hidden="true"
    >
      <rect width="108" height="108" fill="#0054A4" />
      <path d="M30 20 H63 L78 35 V88 H30 Z" fill="#FFFFFF" />
      <rect x="30" y="20" width="7" height="68" fill="#B51F32" />
      <rect x="45" y="47" width="24" height="4" fill="#0054A4" />
      <rect x="45" y="58" width="24" height="4" fill="#0054A4" />
      <rect x="45" y="69" width="17" height="4" fill="#0054A4" />
    </svg>
  );
}

export function HouseIcon({ className = "h-6 w-6" }: { className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.8}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      <path d="M3 10 L12 3 L21 10" />
      <path d="M5 9 V21 H10 V14 H14 V21 H19 V9" />
    </svg>
  );
}

export function AttachmentIcon({
  isImage,
  className = "h-6 w-6",
}: {
  isImage: boolean;
  className?: string;
}) {
  const stroke = isImage ? "#0054A4" : "#B51F32";
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke={stroke}
      strokeWidth={1.6}
      strokeLinecap="round"
      strokeLinejoin="round"
      className={className}
      aria-hidden="true"
    >
      {isImage ? (
        <>
          <rect x="3" y="4" width="18" height="16" />
          <circle cx="16" cy="9" r="1.6" />
          <path d="M4 18 L9 12 L13 16 L16 13 L20 18" />
        </>
      ) : (
        <>
          <path d="M5 2 H14 L20 8 V22 H5 Z" />
          <path d="M14 2 V8 H20" />
          <path d="M8 13 H17" />
          <path d="M8 17 H14" />
        </>
      )}
    </svg>
  );
}
