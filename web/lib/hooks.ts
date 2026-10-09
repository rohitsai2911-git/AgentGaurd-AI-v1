"use client";

import { useCallback, useEffect, useRef, useState } from "react";

import { ApiError } from "./api/client";

/** Normalises anything thrown by the transport into an ApiError. */
export function toApiError(error: unknown): ApiError {
  if (error instanceof ApiError) return error;
  if (error instanceof Error) {
    return new ApiError(error.message, 0, "UNEXPECTED_ERROR", {});
  }
  return new ApiError("An unexpected error occurred.", 0, "UNEXPECTED_ERROR", {});
}

export interface Resource<T> {
  data: T | null;
  error: ApiError | null;
  /** True only on the very first load, so refreshes never blank the screen. */
  loading: boolean;
  refreshing: boolean;
  refresh: () => void;
  setData: (next: T | null) => void;
}

/**
 * Fetches a resource and keeps it fresh without flashing empty states.
 * Latest-request-wins, so a slow response can never overwrite a newer one.
 */
export function useResource<T>(
  fetcher: () => Promise<T>,
  deps: readonly unknown[] = [],
  options: { enabled?: boolean; pollMs?: number } = {},
): Resource<T> {
  const { enabled = true, pollMs } = options;
  const [data, setData] = useState<T | null>(null);
  const [error, setError] = useState<ApiError | null>(null);
  const [loading, setLoading] = useState(enabled);
  const [refreshing, setRefreshing] = useState(false);
  const [nonce, setNonce] = useState(0);

  const requestId = useRef(0);
  const loaded = useRef(false);
  const fetcherRef = useRef(fetcher);
  fetcherRef.current = fetcher;

  const depKey = JSON.stringify(deps);

  useEffect(() => {
    if (!enabled) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const id = (requestId.current += 1);
    setRefreshing(true);
    if (!loaded.current) setLoading(true);

    fetcherRef
      .current()
      .then((value) => {
        if (cancelled || id !== requestId.current) return;
        setData(value);
        setError(null);
      })
      .catch((caught) => {
        if (cancelled || id !== requestId.current) return;
        setError(toApiError(caught));
      })
      .finally(() => {
        if (cancelled || id !== requestId.current) return;
        loaded.current = true;
        setLoading(false);
        setRefreshing(false);
      });

    return () => {
      cancelled = true;
    };
  }, [enabled, nonce, depKey]);

  useEffect(() => {
    if (!pollMs || !enabled) return;
    const timer = setInterval(() => setNonce((value) => value + 1), pollMs);
    return () => clearInterval(timer);
  }, [pollMs, enabled]);

  const refresh = useCallback(() => setNonce((value) => value + 1), []);

  return { data, error, loading, refreshing, refresh, setData };
}

/** Runs a write action once, exposing pending state and the thrown ApiError. */
export function useAction<Args extends unknown[], Result>(
  action: (...args: Args) => Promise<Result>,
) {
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const actionRef = useRef(action);
  actionRef.current = action;

  const run = useCallback(async (...args: Args): Promise<Result | null> => {
    setPending(true);
    setError(null);
    try {
      return await actionRef.current(...args);
    } catch (caught) {
      setError(toApiError(caught));
      return null;
    } finally {
      setPending(false);
    }
  }, []);

  return { run, pending, error, setError };
}

/** Debounces a rapidly changing value — used by every search field. */
export function useDebounced<T>(value: T, delayMs = 250): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

/** Guards against hydration mismatches for anything time-relative. */
export function useHydrated(): boolean {
  const [hydrated, setHydrated] = useState(false);
  useEffect(() => setHydrated(true), []);
  return hydrated;
}

/**
 * Reads a value from localStorage. Settings live on the client only; the
 * backend owns thresholds per test case, so this never pretends to be one.
 */
export function useLocalStorage<T>(key: string, initial: T) {
  const [value, setValue] = useState<T>(initial);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(key);
      if (raw !== null) setValue(JSON.parse(raw) as T);
    } catch {
      /* corrupt or unavailable storage — keep the default */
    }
    setReady(true);
  }, [key]);

  const update = useCallback(
    (next: T) => {
      setValue(next);
      try {
        window.localStorage.setItem(key, JSON.stringify(next));
      } catch {
        /* storage full or blocked — state still updates in memory */
      }
    },
    [key],
  );

  return { value, update, ready };
}