// Small in-memory TTL cache. Stores resolved values only (never pending promises), so
// nothing is shared across request contexts while I/O is in flight.
const store = new Map<string, { exp: number; value: unknown }>();

export async function cached<T>(key: string, ttlMs: number, fn: () => Promise<T>): Promise<T> {
  const hit = store.get(key);
  if (hit && hit.exp > Date.now()) return hit.value as T;
  const value = await fn();
  store.set(key, { exp: Date.now() + ttlMs, value });
  if (store.size > 400) {
    const oldest = store.keys().next().value;
    if (oldest) store.delete(oldest);
  }
  return value;
}

export class ProviderError extends Error {
  constructor(
    public provider: string,
    public code: "timeout" | "http" | "parse" | "auth" | "rate_limit" | "network",
    message: string,
  ) {
    super(message);
  }
}

export async function fetchWithTimeout(url: string, init: RequestInit = {}, ms = 10000) {
  try {
    return await fetch(url, {
      ...init,
      signal: AbortSignal.timeout(ms),
      headers: {
        "User-Agent": "FalconMarketIntelligence/1.0 (educational dashboard)",
        ...(init.headers ?? {}),
      },
    });
  } catch (err) {
    const name = (err as Error)?.name;
    throw new ProviderError(
      "fetch",
      name === "TimeoutError" || name === "AbortError" ? "timeout" : "network",
      `Request failed: ${name ?? "unknown"}`,
    );
  }
}

/** Safe, user-presentable reason for a provider failure (never includes URLs or keys). */
export function failureNote(err: unknown): string {
  if (err instanceof ProviderError) return err.code;
  return "unknown";
}
