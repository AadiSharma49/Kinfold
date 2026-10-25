import { ImageResponse } from "next/og";

export const size = { width: 32, height: 32 };
export const contentType = "image/png";

export default function Icon() {
  return new ImageResponse(
    (
      <div
        style={{
          width: "100%",
          height: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          background: "#1a1816",
          borderRadius: 6,
        }}
      >
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none">
          <path d="M3 4L3 20L12 12L3 4Z" fill="#f7f4ed" />
          <path d="M21 4L21 20L12 12L21 4Z" fill="#f7f4ed" />
        </svg>
      </div>
    ),
    { ...size }
  );
}
