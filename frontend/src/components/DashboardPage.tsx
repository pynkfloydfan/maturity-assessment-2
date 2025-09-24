import createPlotlyComponent from "react-plotly.js/factory";
import Plotly from "plotly.js-dist-min";
import { useSessionContext } from "../context/SessionContext";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import { getDimensionTiles, getRadarFigure, useDashboard } from "../hooks/useDashboard";
import type { DashboardTile } from "../api/types";

const Plot = createPlotlyComponent(Plotly);

function Tile({ tile }: { tile: DashboardTile }) {
  const average = typeof tile.average === "number" ? tile.average.toFixed(2) : "—";
  const coverage = typeof tile.coverage === "number" ? Math.round(tile.coverage * 100) : null;
  const background = tile.color ?? "#f3f5f9";

  return (
    <div
      className="flex min-w-[180px] flex-1 flex-col gap-2 rounded-xl border border-[#e1e6ef] bg-white p-4 shadow-sm"
      style={{ borderColor: tile.color ? tile.color : "#e1e6ef" }}
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
  const { data, figures, loading, error } = useDashboard(activeSessionId);
  const tiles = getDimensionTiles(figures);
  const radar = getRadarFigure(figures);
  usePageBreadcrumb(null);

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
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-semibold text-[#121417]">Dashboard</h1>
          <p className="text-sm text-[#61758a]">Session #{activeSessionId}</p>
        </div>
        <div className="flex gap-3">
          <a
            className="rounded-md border border-[#d0d7e3] px-4 py-2 text-sm font-medium text-[#0d80f2]"
            href={`/api/sessions/${activeSessionId}/exports/json`}
          >
            Download JSON
          </a>
          <a
            className="rounded-md border border-[#d0d7e3] px-4 py-2 text-sm font-medium text-[#0d80f2]"
            href={`/api/sessions/${activeSessionId}/exports/xlsx`}
          >
            Download XLSX
          </a>
        </div>
      </div>

      {loading && <div className="text-sm text-[#61758a]">Loading dashboard…</div>}
      {error && <div className="text-sm text-red-600">{error}</div>}

      {!loading && !error && tiles.length > 0 && (
        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {tiles.map((tile) => (
            <Tile key={tile.id} tile={tile} />
          ))}
        </section>
      )}

      {!loading && !error && radar && (
        <section className="rounded-xl border border-[#e1e6ef] bg-white p-4 shadow-sm">
          <Plot
            data={radar.data}
            layout={{ ...radar.layout, autosize: true, height: 560 }}
            frames={radar.frames ?? []}
            config={{ displaylogo: false, responsive: true }}
            useResizeHandler
            style={{ width: "100%", height: "100%" }}
          />
        </section>
      )}

      {!loading && !error && (!radar || !tiles.length) && (
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-8 text-center text-[#61758a]">
          Not enough ratings yet to build the dashboard visuals.
        </div>
      )}

      {data && data.topic_scores.length > 0 && (
        <section className="rounded-xl border border-[#e1e6ef] bg-white p-4 shadow-sm">
          <h2 className="mb-4 text-lg font-semibold text-[#121417]">Topic ratings</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-[#e1e6ef] text-sm">
              <thead className="bg-[#f9fbfd] text-[#61758a]">
                <tr>
                  <th className="px-4 py-2 text-left">Dimension</th>
                  <th className="px-4 py-2 text-left">Theme</th>
                  <th className="px-4 py-2 text-left">Topic</th>
                  <th className="px-4 py-2 text-left">Score</th>
                  <th className="px-4 py-2 text-left">Source</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#eef2f9] bg-white text-[#121417]">
                {data.topic_scores.map((row) => (
                  <tr key={row.topic_id}>
                    <td className="px-4 py-2">{row.dimension_name}</td>
                    <td className="px-4 py-2">{row.theme_name}</td>
                    <td className="px-4 py-2">{row.topic_name}</td>
                    <td className="px-4 py-2">{row.score.toFixed(2)}</td>
                    <td className="px-4 py-2">{row.source === "computed" ? "Computed" : "Rating"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </div>
  );
}
