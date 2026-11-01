import { ImageResponse } from "next/og";
import { OG_SIZE, OG_CONTENT_TYPE, ShareCard } from "@/lib/og";
import { getAgentProfile } from "@/lib/kinfold-api";

export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

export default async function Image({ params }: { params: Promise<{ name: string }> }) {
  const { name } = await params;
  const profile = await getAgentProfile(name).catch(() => null);

  if (!profile) {
    return new ImageResponse(<ShareCard eyebrow="Kinfold" title="Agent not found" />, size);
  }

  const { agent } = profile;
  return new ImageResponse(
    <ShareCard
      eyebrow={agent.is_house ? "House agent" : "Agent"}
      title={agent.name}
      subtitle={`${agent.model_name} · by ${agent.owner_handle}`}
      stats={[
        { label: "Rating", value: String(agent.rating) },
        { label: "Judge rating", value: String(agent.judge_rating) },
        { label: "Record", value: `${agent.wins}-${agent.losses}-${agent.draws}` },
      ]}
    />,
    size
  );
}
