export function Logo({
  size = 24,
  className = "",
}: {
  size?: number;
  className?: string;
}) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden="true"
      className={className}
    >
      <path d="M3 4L3 20L12 12L3 4Z" fill="currentColor" />
      <path d="M21 4L21 20L12 12L21 4Z" fill="currentColor" />
    </svg>
  );
}

export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <Logo size={18} className="text-accent" />
      <span className="font-mono text-lg font-semibold tracking-tight">
        kinfold
      </span>
    </span>
  );
}
