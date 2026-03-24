/**
 * useOfflineQuery — React Query wrapper with offline cache fallback.
 *
 * Fetches from network first, caches results to AsyncStorage.
 * When offline, serves cached data transparently.
 */

import { useQuery, type UseQueryOptions, type QueryKey } from "@tanstack/react-query";
import { fetchWithCache } from "@/lib/offline-cache";

/**
 * Like useQuery, but with automatic offline cache support.
 * Wraps the queryFn with fetchWithCache so results are persisted
 * and served from cache when the network is unavailable.
 */
export function useOfflineQuery<TData>(
  options: UseQueryOptions<TData, Error, TData, QueryKey> & {
    cacheKey: string;
  },
) {
  const { cacheKey, queryFn, ...rest } = options;

  return useQuery<TData, Error, TData, QueryKey>({
    ...rest,
    queryFn: queryFn
      ? () => fetchWithCache(cacheKey, queryFn as () => Promise<TData>)
      : undefined,
    // Keep stale data while revalidating — better offline UX
    staleTime: 30_000,
    // Don't garbage collect cached data for 24h
    gcTime: 24 * 60 * 60 * 1000,
    // Show stale data immediately while refetching
    refetchOnMount: "always",
  });
}
