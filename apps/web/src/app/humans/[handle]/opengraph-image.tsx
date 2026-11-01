import { ImageResponse } from "next/og";
import { OG_SIZE, OG_CONTENT_TYPE, ShareCard } from "@/lib/og";
import { getOwnerProfile } from "@/lib/kinfold-api";

export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image({ params }: { params: Promise<{ handle: string }> }) {
  const { handle } = await params;
  const profile = await getOwnerProfile(handle).catch(() => null);

  if (!profile) {
    return new ImageResponse(<ShareCard eyebrow="Kinfold" title="Profile not found" />, size);
  }

  const history = profile.human_duel_history;
  const wins = history.filter((h) => h.result === "win").length;
  const losses = history.filter((h) => h.result === "loss").length;
  const draws = history.filter((h) => h.result === "draw").length;

  return new ImageResponse(
    <ShareCard
      eyebrow="Self-declared human entrant"
      title={profile.owner.handle}
      subtitle={`${history.length} duel${history.length === 1 ? "" : "s"} entered against AI agents`}
      stats={[
        { label: "Beat the AI", value: String(wins) },
        { label: "Lost", value: String(losses) },
        { label: "Drew", value: String(draws) },
      ]}
    />,
    size
  );
}
