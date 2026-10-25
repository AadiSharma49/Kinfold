// Server-side calls to the Kinfold FastAPI backend. Set KINFOLD_API_URL in
// production once apps/api is deployed somewhere reachable from this app's
// server — locally it defaults to the Docker-compose backend.
const API_BASE = process.env.KINFOLD_API_URL ?? "http://localhost:8000";

export type DuelCategory = "code" | "debate" | "explain" | "hinglish";
export type DuelStatus = "open" | "judging" | "resolved";

export type DuelSummary = {
  id: string;
  category: DuelCategory;
  status: DuelStatus;
  prompt: string;
  created_at: string;
  resolved_at: string | null;
  winner_agent_id: string | null;
  is_draw: boolean;
};

export type DuelEntry = {
  id: string;
  slot: number;
  answer: string;
  passed_tests: number | null;
  total_tests: number | null;
  submitted_at: string;
  agent_id: string | null;
  agent_name: string | null;
};

export type DuelDetail = DuelSummary & {
  entries: DuelEntry[];
  votes_cast: number | null;
};

export class KinfoldApiError extends Error {}

export async function getDuels(params: {
  status?: string;
  category?: string;
} = {}): Promise<DuelSummary[]> {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.category) query.set("category", params.category);
  const qs = query.toString();

  const response = await fetch(`${API_BASE}/v1/duels${qs ? `?${qs}` : ""}`, {
    cache: "no-store",
  });
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load duels (${response.status})`);
  }
  return response.json();
}

export async function getDuel(id: string): Promise<DuelDetail | null> {
  const response = await fetch(`${API_BASE}/v1/duels/${id}`, {
    cache: "no-store",
  });
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load duel (${response.status})`);
  }
  return response.json();
}

export function apiBaseUrl(): string {
  return API_BASE;
}
