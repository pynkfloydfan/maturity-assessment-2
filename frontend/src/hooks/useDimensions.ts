import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { Dimension } from "../api/types";

export function useDimensions() {
  const [dimensions, setDimensions] = useState<Dimension[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDimensions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<Dimension[]>("/api/dimensions");
      setDimensions(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dimensions");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDimensions();
  }, [fetchDimensions]);

  useEffect(() => {
    const handler = () => {
      fetchDimensions();
    };
    window.addEventListener("focus", handler);
    return () => window.removeEventListener("focus", handler);
  }, [fetchDimensions]);

  return { dimensions, loading, error, refresh: fetchDimensions };
}
