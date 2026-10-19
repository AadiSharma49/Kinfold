import { z } from "zod";

export const roles = [
  "watcher",
  "agent builder",
  "open model trainer",
  "researcher",
  "other",
] as const;

export const waitlistSchema = z.object({
  email: z.string().trim().toLowerCase().email(),
  role: z.enum(roles),
  bring: z.string().trim().max(280).optional().or(z.literal("")),
  company: z.string().optional().or(z.literal("")),
});

export type WaitlistEntry = z.infer<typeof waitlistSchema>;

const WINDOW_MS = 10 * 60 * 1000;
const MAX_REQUESTS = 5;

const requestLog = new Map<string, number[]>();

export function isRateLimited(ip: string): boolean {
  const now = Date.now();
  const timestamps = (requestLog.get(ip) ?? []).filter(
    (t) => now - t < WINDOW_MS
  );
  if (timestamps.length >= MAX_REQUESTS) {
    requestLog.set(ip, timestamps);
    return true;
  }
  timestamps.push(now);
  requestLog.set(ip, timestamps);
  return false;
}
