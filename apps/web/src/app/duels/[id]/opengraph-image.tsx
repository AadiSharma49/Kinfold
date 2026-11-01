import { ImageResponse } from "next/og";
import { OG_SIZE, OG_CONTENT_TYPE, ShareCard } from "@/lib/og";
import { getDuel } from "@/lib/kinfold-api";

export const size = OG_SIZE;
export const contentType = OG_CONTENT_TYPE;

const CATEGORY_LABELS: Record<string, string> = {
  code: "Code duel",
  debate: "Debate duel",
  explain: "Explain duel",
  hinglish: "Hinglish duel",
};

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const duel = await getDuel(id).catch(() => null);

  if (!duel) {
    return new ImageResponse(
      <ShareCard eyebrow="Kinfold" title="Duel not found" />,
      size
    );
  }

  const eyebrow = CATEGORY_LABELS[duel.category] ?? duel.category;
  let subtitle: string | undefined;
  const stats: { label: string; value: string }[] = [{ label: "Status", value: duel.status }];

  if (duel.status === "resolved") {
    subtitle = duel.is_draw ? "Ended in a draw." : "Decided — see who won.";
  } else {
    subtitle = "Judged by hidden tests or blind human vote.";
  }

  return new ImageResponse(
    <ShareCard eyebrow={eyebrow} title={duel.prompt} subtitle={subtitle} stats={stats} />,
    size
  );
}
