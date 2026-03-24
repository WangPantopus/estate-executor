/**
 * Offline cache — persists React Query data to AsyncStorage.
 *
 * Caches recently viewed matters and tasks so they're readable offline.
 * Uses a simple key-value approach with TTL for cache invalidation.
 */

import AsyncStorage from "@react-native-async-storage/async-storage";

const CACHE_PREFIX = "ee_cache:";
const CACHE_TTL_MS = 24 * 60 * 60 * 1000; // 24 hours

interface CacheEntry<T> {
  data: T;
  timestamp: number;
}

// ─── Core cache operations ──────────────────────────────────────────────────

export async function cacheSet<T>(key: string, data: T): Promise<void> {
  try {
    const entry: CacheEntry<T> = {
      data,
      timestamp: Date.now(),
    };
    await AsyncStorage.setItem(
      CACHE_PREFIX + key,
      JSON.stringify(entry),
    );
  } catch (error) {
    console.warn("Cache write failed:", error);
  }
}

export async function cacheGet<T>(key: string): Promise<T | null> {
  try {
    const raw = await AsyncStorage.getItem(CACHE_PREFIX + key);
    if (!raw) return null;

    const entry: CacheEntry<T> = JSON.parse(raw);

    // Check TTL
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
      await AsyncStorage.removeItem(CACHE_PREFIX + key);
      return null;
    }

    return entry.data;
  } catch (error) {
    console.warn("Cache read failed:", error);
    return null;
  }
}

export async function cacheRemove(key: string): Promise<void> {
  try {
    await AsyncStorage.removeItem(CACHE_PREFIX + key);
  } catch (error) {
    console.warn("Cache remove failed:", error);
  }
}

// ─── Domain-specific cache keys ─────────────────────────────────────────────

export function mattersCacheKey(firmId: string): string {
  return `matters:${firmId}`;
}

export function matterDetailCacheKey(firmId: string, matterId: string): string {
  return `matter:${firmId}:${matterId}`;
}

export function tasksCacheKey(firmId: string, matterId: string): string {
  return `tasks:${firmId}:${matterId}`;
}

export function taskDetailCacheKey(firmId: string, matterId: string, taskId: string): string {
  return `task:${firmId}:${matterId}:${taskId}`;
}

// ─── Cache-aware fetch wrapper ──────────────────────────────────────────────

/**
 * Fetch with offline fallback: tries the network first, falls back to cache.
 * On success, updates the cache for future offline use.
 */
export async function fetchWithCache<T>(
  cacheKey: string,
  fetchFn: () => Promise<T>,
): Promise<T> {
  try {
    // Try network first
    const data = await fetchFn();
    // Cache the result for offline use
    await cacheSet(cacheKey, data);
    return data;
  } catch (error) {
    // Network failed — try cache
    const cached = await cacheGet<T>(cacheKey);
    if (cached !== null) {
      return cached;
    }
    // No cache — re-throw original error
    throw error;
  }
}

// ─── Clear all cached data ──────────────────────────────────────────────────

export async function clearAllCache(): Promise<void> {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const cacheKeys = keys.filter((k) => k.startsWith(CACHE_PREFIX));
    if (cacheKeys.length > 0) {
      await AsyncStorage.multiRemove(cacheKeys);
    }
  } catch (error) {
    console.warn("Cache clear failed:", error);
  }
}

// ─── Cache stats (for debugging) ────────────────────────────────────────────

export async function getCacheStats(): Promise<{
  entryCount: number;
  totalSizeEstimate: number;
}> {
  try {
    const keys = await AsyncStorage.getAllKeys();
    const cacheKeys = keys.filter((k) => k.startsWith(CACHE_PREFIX));
    let totalSize = 0;

    for (const key of cacheKeys) {
      const value = await AsyncStorage.getItem(key);
      if (value) totalSize += value.length;
    }

    return { entryCount: cacheKeys.length, totalSizeEstimate: totalSize };
  } catch {
    return { entryCount: 0, totalSizeEstimate: 0 };
  }
}
