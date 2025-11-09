import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type { DimensionAssessmentResponse } from "../api/types";

export function useDimensionAssessment(dimensionId: number | null, sessionId: number | null) {
  const [data, setData] = useState<DimensionAssessmentResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDimensionAssessment = useCallback(async () => {
    if (!dimensionId) {
      setData(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const params = sessionId ? { session_id: sessionId } : undefined;
      const response = await apiGet<DimensionAssessmentResponse>(
        `/api/dimensions/${dimensionId}/assessment`,
        params,
      );
      setData(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load assessment data");
    } finally {
      setLoading(false);
    }
  }, [dimensionId, sessionId]);

  useEffect(() => {
    fetchDimensionAssessment();
  }, [fetchDimensionAssessment]);

  return { data, loading, error, refresh: fetchDimensionAssessment };
}
