import { useCallback, useEffect, useState } from "react";

const CACHE_FRESH_MS = 15 * 1000;
const CACHE_TTL_MS = 2 * 60 * 1000;
const MAX_CACHE_ENTRIES = 80;
type CacheEntry = { storedAt: number; value: unknown };
const responseCache = new Map<string, CacheEntry>();
const pendingLoads = new Map<string, Promise<unknown>>();

function cachedEntry(key: string): CacheEntry | null {
  const cached = responseCache.get(key);
  if (!cached) return null;
  if (Date.now() - cached.storedAt > CACHE_TTL_MS) {
    responseCache.delete(key);
    return null;
  }
  return cached;
}

function cachedValue<T>(key: string): T | null {
  return cachedEntry(key)?.value as T | null;
}

function storeValue<T>(key: string, value: T) {
  responseCache.delete(key);
  responseCache.set(key, { storedAt: Date.now(), value });
  while (responseCache.size > MAX_CACHE_ENTRIES) {
    const oldest = responseCache.keys().next().value as string | undefined;
    if (!oldest) break;
    responseCache.delete(oldest);
  }
}

function loadOnce<T>(key: string, loader: () => Promise<T>): Promise<T> {
  const pending = pendingLoads.get(key) as Promise<T> | undefined;
  if (pending) return pending;
  const request = loader().finally(() => pendingLoads.delete(key));
  pendingLoads.set(key, request);
  return request;
}

type ApiState<T> = { key: string; data: T | null; error: Error | null; loading: boolean };

function initialState<T>(key: string): ApiState<T> {
  const cached = cachedValue<T>(key);
  return { key, data: cached, error: null, loading: !cached };
}

export function useApi<T>(loader: () => Promise<T>, key: string) {
  const [state, setState] = useState<ApiState<T>>(() => initialState<T>(key));
  const [revision, setRevision] = useState(0);

  const reload = useCallback(() => {
    responseCache.delete(key);
    setRevision((value) => value + 1);
  }, [key]);

  useEffect(() => {
    let active = true;
    const entry = cachedEntry(key);
    const cached = entry ? entry.value as T : null;
    setState({ key, data: cached, error: null, loading: !cached });
    if (entry && Date.now() - entry.storedAt <= CACHE_FRESH_MS) {
      return () => {
        active = false;
      };
    }
    loadOnce(key, loader)
      .then((value) => {
        storeValue(key, value);
        if (active) setState({ key, data: value, error: null, loading: false });
      })
      .catch((reason: unknown) => {
        if (active && !cached) {
          setState({ key, data: null, error: reason instanceof Error ? reason : new Error(String(reason)), loading: false });
        }
      });
    return () => {
      active = false;
    };
  }, [key, revision]);

  const current = state.key === key ? state : initialState<T>(key);
  return { data: current.data, error: current.error, loading: current.loading, reload };
}
