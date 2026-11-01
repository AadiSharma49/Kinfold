// Shared layout for every opengraph-image.tsx route. Plain and honest by
// design, matching the site: no gradients, no stock-photo energy — a
// wordmark, a real headline built from real data, and a row of real
// numbers. See docs/decisions.md, 2026-11-01.
export const OG_SIZE = { width: 1200, height: 630 };
export const OG_CONTENT_TYPE = "image/png";

const COLORS = {
  background: "#f7f4ed",
  foreground: "#1a1816",
  muted: "#5b564e",
  border: "#ddd6c7",
  accent: "#b8451f",
  accentSoft: "#f0ddd2",
};

export function ShareCard({
  eyebrow,
  title,
  subtitle,
  stats,
}: {
  eyebrow: string;
  title: string;
  subtitle?: string;
  stats?: { label: string; value: string }[];
}) {
  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        background: COLORS.background,
        color: COLORS.foreground,
        padding: "64px 72px",
        fontFamily: "sans-serif",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <div
          style={{
            width: 28,
            height: 28,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            background: COLORS.foreground,
            borderRadius: 6,
          }}
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none">
            <path d="M3 4L3 20L12 12L3 4Z" fill={COLORS.background} />
            <path d="M21 4L21 20L12 12L21 4Z" fill={COLORS.background} />
          </svg>
        </div>
        <span style={{ fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em" }}>Kinfold</span>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
        <span
          style={{
            fontSize: 20,
            color: COLORS.accent,
            textTransform: "uppercase",
            letterSpacing: "0.06em",
            fontWeight: 600,
          }}
        >
          {eyebrow}
        </span>
        <span
          style={{
            fontSize: 52,
            fontWeight: 600,
            lineHeight: 1.15,
            letterSpacing: "-0.02em",
            maxWidth: 1000,
          }}
        >
          {title}
        </span>
        {subtitle && <span style={{ fontSize: 26, color: COLORS.muted }}>{subtitle}</span>}
      </div>

      {stats && stats.length > 0 && (
        <div style={{ display: "flex", gap: 16 }}>
          {stats.map((stat) => (
            <div
              key={stat.label}
              style={{
                display: "flex",
                flexDirection: "column",
                gap: 4,
                padding: "16px 24px",
                background: COLORS.accentSoft,
                borderRadius: 10,
              }}
            >
              <span
                style={{
                  fontSize: 15,
                  color: COLORS.accent,
                  textTransform: "uppercase",
                  letterSpacing: "0.04em",
                }}
              >
                {stat.label}
              </span>
              <span style={{ fontSize: 28, fontWeight: 600 }}>{stat.value}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
