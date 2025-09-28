import { useMemo } from "react";
import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { useSessionContext } from "../context/SessionContext";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import { getDimensionTiles, getRadarFigure, useDashboard } from "../hooks/useDashboard";
import type { DashboardTile } from "../api/types";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "./ui/tabs";

const Plot = createPlotlyComponent(Plotly);

function Tile({ tile }: { tile: DashboardTile }) {
  const average = typeof tile.average === "number" ? tile.average.toFixed(2) : "—";
  const coverage = typeof tile.coverage === "number" ? Math.round(tile.coverage * 100) : null;
  const background = tile.color ?? "#f3f5f9";

  return (
    <div
      className="heatmap-tile flex min-w-[180px] flex-col gap-2 rounded-xl border-3 border-[#e1e6ef] bg-white p-4 shadow-sm"
      style={tile.color ? { borderColor: tile.color } : undefined}
    >
      <span className="text-sm font-medium text-[#61758a]">{tile.name}</span>
      <div className="flex items-baseline gap-2">
        <span className="text-3xl font-semibold text-[#121417]">{average}</span>
        {coverage !== null && <span className="text-xs text-[#61758a]">coverage {coverage}%</span>}
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-[#eef2f9]">
        <div
          className="h-full"
          style={{ width: `${Math.min(Math.max(coverage ?? 0, 0), 100)}%`, background }}
        />
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const { activeSessionId } = useSessionContext();
  const { figures, loading, error } = useDashboard(activeSessionId);
  const tiles = getDimensionTiles(figures);
  const radar = getRadarFigure(figures);
  usePageBreadcrumb(null);

  const tileMetrics = useMemo(() => {
    if (!tiles.length) {
      return { coverage: null as number | null, average: null as number | null };
    }
    let coverageSum = 0;
    let coverageCount = 0;
    let averageSum = 0;
    let averageCount = 0;
    tiles.forEach((tile) => {
      if (typeof tile.coverage === "number") {
        coverageSum += tile.coverage;
        coverageCount += 1;
      }
      if (typeof tile.average === "number") {
        averageSum += tile.average;
        averageCount += 1;
      }
    });
    return {
      coverage: coverageCount ? Math.round((coverageSum / coverageCount) * 100) : null,
      average: averageCount ? averageSum / averageCount : null,
    };
  }, [tiles]);

  const coverageDisplay = tileMetrics.coverage == null ? "–" : `${tileMetrics.coverage}%`;
  const averageDisplay = tileMetrics.average == null ? "–" : tileMetrics.average.toFixed(1);
  const tileCount = tiles.length;
  const hasTiles = !loading && !error && tileCount > 0;
  const hasRadar = !loading && !error && Boolean(radar);

  if (!activeSessionId) {
    return (
      <div className="mx-auto max-w-5xl px-6 py-10">
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-10 text-center">
          <h2 className="mb-2 text-xl font-semibold text-[#121417]">Select a session</h2>
          <p className="text-[#61758a]">Choose or create an assessment session in the header to view dashboards.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <div className="pill">Dashboard</div>
        <div>
          <h1>Operational maturity snapshot</h1>
          <p>
            Review resilience performance for session #{activeSessionId} using the heatmap or radar
            visualisations. Export the underlying data to continue your analysis.
          </p>
        </div>
        <div className="status-card">
          <div className="status-item">
            <div className="status-label">Active session</div>
            <div className="status-value">#{activeSessionId}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Maturity tiles</div>
            <div className="status-value">{loading ? "–" : tileCount || "–"}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Average coverage / score</div>
            <div className="status-value">{loading ? "–" : `${coverageDisplay} · ${averageDisplay}`}</div>
            <div className="status-note">Heatmap coverage · mean score</div>
          </div>
        </div>
      </div>

      <div className="page-toolbar">
        <div className="page-toolbar__summary">Session #{activeSessionId}</div>
        <div className="page-toolbar__actions">
          <a
            className="btn-secondary"
            href={`/api/sessions/${activeSessionId}/exports/json`}
          >
            Download JSON
          </a>
          <a
            className="btn-secondary"
            href={`/api/sessions/${activeSessionId}/exports/xlsx`}
          >
            Download XLSX
          </a>
        </div>
      </div>

      {loading && <div className="info-banner">Loading dashboard…</div>}
      {error && <div className="info-banner error">{error}</div>}

      <Tabs defaultValue="heatmap" className="dashboard-tabs">
        <TabsList className="dashboard-tabs__list">
          <TabsTrigger value="heatmap">Maturity Heatmap</TabsTrigger>
          <TabsTrigger value="radar">Radar plot</TabsTrigger>
        </TabsList>

        <TabsContent value="heatmap">
          {hasTiles ? (
            <section className="dashboard-panel">
              <div className="heatmap-grid">
                {tiles.map((tile) => (
                  <Tile key={tile.id} tile={tile} />
                ))}
              </div>
            </section>
          ) : (
            <div className="info-banner" role="status">
              {loading ? "Building maturity tiles…" : "No maturity data available yet."}
            </div>
          )}
        </TabsContent>

        <TabsContent value="radar">
          {hasRadar ? (
            <section className="dashboard-panel">
              <div className="radar-wrapper">
                <Plot
                  data={radar!.data}
                  layout={{ ...radar!.layout, autosize: true, height: 560 }}
                  frames={radar!.frames ?? []}
                  config={{ displaylogo: false, responsive: true }}
                  useResizeHandler
                  style={{ width: "100%", height: "100%" }}
                />
              </div>
            </section>
          ) : (
            <div className="info-banner" role="status">
              {loading ? "Preparing radar visual…" : "Radar plot unavailable for this session."}
            </div>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
