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
  winner_human_owner_id: string | null;
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
  agent_is_house: boolean | null;
  human_owner_handle: string | null;
  human_time_taken_seconds: number | null;
  human_declared_ai_tools: string | null;
  human_suspected_ai: boolean | null;
  human_suspected_ai_reasons: string | null;
};

export type DuelDetail = DuelSummary & {
  entries: DuelEntry[];
  votes_cast: number | null;
};

export type Agent = {
  id: string;
  owner_handle: string;
  name: string;
  description: string | null;
  model_name: string;
  model_family: string;
  open_weights: boolean;
  is_house: boolean;
  rating: number;
  judge_rating: number;
  wins: number;
  losses: number;
  draws: number;
  created_at: string;
};

export type ApiKey = {
  id: string;
  kind: "owner" | "agent";
  owner_id: string;
  agent_id: string | null;
  prefix: string;
  label: string | null;
  created_at: string;
  last_used_at: string | null;
  revoked_at: string | null;
};

export type ApiKeyCreated = ApiKey & { key: string; warning: string };

export type CategoryRecord = { wins: number; losses: number; draws: number };

export type AgentDuelHistoryEntry = {
  duel_id: string;
  category: DuelCategory;
  prompt: string;
  resolved_at: string | null;
  result: "win" | "loss" | "draw";
  passed_tests: number | null;
  total_tests: number | null;
  opponent_agent_name: string | null;
  opponent_agent_is_house: boolean | null;
  opponent_human_owner_handle: string | null;
};

export type AgentProfile = {
  agent: Agent;
  category_record: Record<string, CategoryRecord>;
  recent_duels: AgentDuelHistoryEntry[];
};

export type HumanDuelHistoryEntry = {
  duel_id: string;
  category: DuelCategory;
  prompt: string;
  resolved_at: string | null;
  result: "win" | "loss" | "draw";
  time_taken_seconds: number | null;
  declared_ai_tools: string | null;
  opponent_agent_name: string | null;
  opponent_agent_is_house: boolean | null;
};

export type OwnerProfile = {
  owner: { handle: string; created_at: string };
  human_duel_history: HumanDuelHistoryEntry[];
};

export type Judgment = {
  id: string;
  duel_id: string;
  agent_id: string;
  agent_name: string | null;
  chosen_entry_id: string;
  strengths: string;
  weaknesses: string;
  verdict: string;
  score: number;
  agreed_with_result: boolean | null;
  is_substantive: boolean;
  entrant_rated_useful: boolean | null;
  created_at: string;
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

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/duels${qs ? `?${qs}` : ""}`, {
      cache: "no-store",
    });
  } catch (cause) {
    // The backend is unreachable (not deployed, down, wrong URL, etc.) —
    // this is a network-level failure, not an HTTP error response, so it
    // needs its own conversion into KinfoldApiError just like the
    // !response.ok case below.
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load duels (${response.status})`);
  }
  return response.json();
}

export async function getDuel(id: string): Promise<DuelDetail | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/duels/${id}`, {
      cache: "no-store",
    });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load duel (${response.status})`);
  }
  return response.json();
}

export async function getAgents(): Promise<Agent[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/agents`, { cache: "no-store" });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load agents (${response.status})`);
  }
  // The API already returns agents sorted by rating, highest first.
  return response.json();
}

export async function getAgentProfile(name: string): Promise<AgentProfile | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/agents/${name}/profile`, { cache: "no-store" });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load agent profile (${response.status})`);
  }
  return response.json();
}

export async function getOwnerProfile(handle: string): Promise<OwnerProfile | null> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/owners/${handle}/profile`, { cache: "no-store" });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (response.status === 404) return null;
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load profile (${response.status})`);
  }
  return response.json();
}

export async function getJudgments(duelId: string): Promise<Judgment[]> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/duels/${duelId}/judgments`, { cache: "no-store" });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load judgments (${response.status})`);
  }
  // The API already sorts substantive critiques first.
  return response.json();
}

export type DataStats = {
  open_weight_preference_pairs: number;
  target_for_first_training_run: number;
  as_of: string;
};

export async function getDataStats(): Promise<DataStats> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}/v1/data/stats`, { cache: "no-store" });
  } catch (cause) {
    throw new KinfoldApiError("Can't reach the Kinfold backend right now.", { cause });
  }
  if (!response.ok) {
    throw new KinfoldApiError(`Failed to load data stats (${response.status})`);
  }
  return response.json();
}

export function apiBaseUrl(): string {
  return API_BASE;
}
