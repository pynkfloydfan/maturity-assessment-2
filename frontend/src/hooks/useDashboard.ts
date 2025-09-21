import { useCallback, useEffect, useState } from "react";
import { apiGet } from "../api/client";
import type {
  DashboardData,
  DashboardFiguresResponse,
  DashboardTile,
  PlotlyFigure,
} from "../api/types";

interface DashboardState {
  data: DashboardData | null;
  figures: DashboardFiguresResponse | null;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export function useDashboard(sessionId: number | null): DashboardState {
  const [data, setData] = useState<DashboardData | null>(null);
  const [figures, setFigures] = useState<DashboardFiguresResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboard = useCallback(async () => {
    if (!sessionId) {
      setData(null);
      setFigures(null);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      const [structure, visuals] = await Promise.all([
        apiGet<DashboardData>(`/api/sessions/${sessionId}/dashboard`),
        apiGet<DashboardFiguresResponse>(`/api/sessions/${sessionId}/dashboard/figures`),
      ]);
      setData(structure);
      setFigures(visuals);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
      setData(null);
      setFigures(null);
    } finally {
      setLoading(false);
    }
  }, [sessionId]);

  useEffect(() => {
    fetchDashboard();
  }, [fetchDashboard]);

  return {
    data,
    figures,
    loading,
    error,
    refresh: fetchDashboard,
  };
}

export function getDimensionTiles(figures: DashboardFiguresResponse | null): DashboardTile[] {
  return figures?.tiles ?? [];
}

export function getRadarFigure(figures: DashboardFiguresResponse | null): PlotlyFigure | null {
  return figures?.radar ?? null;
}
