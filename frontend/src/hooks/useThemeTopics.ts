import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { ThemeTopicsResponse } from "../api/types";

interface Options {
  themeId: number | null;
  sessionId: number | null;
}

export function useThemeTopics({ themeId, sessionId }: Options) {
  const [data, setData] = useState<ThemeTopicsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThemeTopics = useCallback(async () => {
    if (!themeId) {
      setData(null);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const params = sessionId ? { session_id: sessionId } : undefined;
      const result = await apiGet<ThemeTopicsResponse>(`/api/themes/${themeId}/topics`, params);
      setData(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load topics");
    } finally {
      setLoading(false);
    }
  }, [themeId, sessionId]);

  useEffect(() => {
    fetchThemeTopics();
  }, [fetchThemeTopics]);

  return { data, loading, error, refresh: fetchThemeTopics };
}
