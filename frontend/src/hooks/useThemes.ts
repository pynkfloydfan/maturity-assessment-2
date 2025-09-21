import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { Theme } from "../api/types";

export function useThemes(dimensionId: number | null) {
  const [themes, setThemes] = useState<Theme[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThemes = useCallback(async () => {
    if (!dimensionId) {
      setThemes([]);
      return;
    }
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<Theme[]>(`/api/dimensions/${dimensionId}/themes`);
      setThemes(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load themes");
    } finally {
      setLoading(false);
    }
  }, [dimensionId]);

  useEffect(() => {
    fetchThemes();
  }, [fetchThemes]);

  useEffect(() => {
    if (!dimensionId) {
      return;
    }
    const handler = () => fetchThemes();
    window.addEventListener("focus", handler);
    return () => window.removeEventListener("focus", handler);
  }, [fetchThemes, dimensionId]);

  return { themes, loading, error, refresh: fetchThemes };
}
