import pandas as pd
import numpy as np
import plotly.graph_objects as go

def make_resilience_radar_with_theme_bars(
    scores: pd.DataFrame,
    dimension_order: list[str] | None = None,
    title: str | None = None,
    max_score: float = 5.0,
    bar_base: float = 5.35,          # start of mini bars (just beyond the 5-ring)
    bar_total_height: float = 0.8,   # visual height representing max_score
    bar_width_deg: float = 1.4,      # angular width of each theme bar
    bar_gap_deg: float = 0.6         # angular gap between theme bars
) -> go.Figure:
    """
    Build a 9-spoke radar chart (one spoke per Dimension) with grouped mini bars at each spoke tip.
    Each mini bar corresponds to a Theme within that Dimension, with bar height = average score of that Theme.
    Bars are plotted just beyond the 5-ring to keep the radar readable.

    Parameters
    ----------
    scores : DataFrame with columns ["Dimension", "Theme", "Question", "Score"] (Score 0..5)
    dimension_order : Optional list[str] to control clockwise spoke order (12 o’clock start)
    title : Optional figure title; if None, derived from lowest mean dimension
    max_score : Max score on your maturity scale (default 5.0)
    bar_base : Radial position where mini bars start (beyond the 5-ring)
    bar_total_height : Visual height that represents max_score
    bar_width_deg : Angular width of each mini bar (degrees)
    bar_gap_deg : Angular gap between adjacent mini bars (degrees)

    Returns
    -------
    plotly.graph_objects.Figure
    """
    # -------- input validation --------
    required_cols = {"Dimension", "Theme", "Question", "Score"}
    missing = required_cols - set(scores.columns)
    if missing:
        raise ValueError(f"Scores DataFrame missing required columns: {sorted(missing)}")
    if not np.issubdtype(scores["Score"].dtype, np.number):
        raise TypeError("Column 'Score' must be numeric (0..5).")

    # -------- summaries --------
    dim_summary = (
        scores.groupby("Dimension", as_index=False)
              .agg(mean_score=("Score", "mean"))
    )
    theme_summary = (
        scores.groupby(["Dimension", "Theme"], as_index=False)
              .agg(theme_mean=("Score", "mean"))
    )

    # -------- dimension order & angles --------
    if dimension_order is None:
        # Use the order as they appear in the input (stable) or alphabetical fallback
        # Here we keep stable input order:
        dims = list(pd.unique(scores["Dimension"]))
    else:
        dims = dimension_order
        # sanity: ensure all dims are present
        missing_dims = set(dims) - set(dim_summary["Dimension"])
        if missing_dims:
            raise ValueError(f"dimension_order includes unknown dimensions: {sorted(missing_dims)}")

    # assign equally spaced angles (degrees)
    angles = np.linspace(0, 360, len(dims), endpoint=False)
    dim_angles = pd.DataFrame({"Dimension": dims, "theta": angles})

    dim_summary = dim_summary.merge(dim_angles, on="Dimension", how="right")
    theme_summary = theme_summary.merge(dim_angles, on="Dimension", how="left")

    # -------- colour gradient (colour-blind safe) --------
    def hex_to_rgb(h: str) -> tuple[int, int, int]:
        h = h.lstrip("#")
        return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

    def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
        return "#" + "".join(f"{c:02X}" for c in rgb)

    def lerp(a: float, b: float, t: float) -> float:
        return a + (b - a) * t

    # Stops: 0:#D73027, 2:#FC8D59, 3:#FEE08B, 4:#91CF60, 5:#1A9850
    stops = [(0.0,"#D73027"), (2.0,"#FC8D59"), (3.0,"#FEE08B"), (4.0,"#91CF60"), (5.0,"#1A9850")]
    def gradient_color(value: float) -> str:
        v = float(value)
        if v <= stops[0][0]:
            return stops[0][1]
        if v >= stops[-1][0]:
            return stops[-1][1]
        for i in range(len(stops) - 1):
            v0, c0 = stops[i]
            v1, c1 = stops[i + 1]
            if v0 <= v <= v1:
                t = 0 if v1 == v0 else (v - v0) / (v1 - v0)
                r0, g0, b0 = hex_to_rgb(c0)
                r1, g1, b1 = hex_to_rgb(c1)
                r = int(round(lerp(r0, r1, t)))
                g = int(round(lerp(g0, g1, t)))
                b = int(round(lerp(b0, b1, t)))
                return rgb_to_hex((r, g, b))
        return stops[-1][1]

    dim_summary["mean_color"] = dim_summary["mean_score"].apply(gradient_color)
    theme_summary["bar_color"] = theme_summary["theme_mean"].apply(gradient_color)

    # -------- figure --------
    fig = go.Figure()

    # Radar polygon (connect dimension means)
    r_vals = dim_summary["mean_score"].tolist() + [dim_summary["mean_score"].iloc[0]]
    theta_vals = dim_summary["theta"].tolist() + [dim_summary["theta"].iloc[0]]
    fig.add_trace(go.Scatterpolar(
        r=r_vals,
        theta=theta_vals,
        mode="lines",
        line=dict(color="#666666", width=1.5),
        fill="toself",
        fillcolor="rgba(0,0,0,0.08)",
        name="Mean Score (0–5)",
        hoverinfo="skip"
    ))

    # Mean markers per dimension (colour by gradient)
    fig.add_trace(go.Scatterpolar(
        r=dim_summary["mean_score"],
        theta=dim_summary["theta"],
        mode="markers+text",
        marker=dict(size=10, color=dim_summary["mean_color"]),
        text=[f"{m:.1f}" for m in dim_summary["mean_score"]],
        textposition="top center",
        name="Mean by Dimension",
        hovertemplate="<b>%{customdata[0]}</b><br>Mean: %{customdata[1]:.2f}<extra></extra>",
        customdata=np.stack([dim_summary["Dimension"], dim_summary["mean_score"]], axis=1)
    ))

    # Grouped mini bars at spoke tip (one bar per Theme)
    for _, drow in dim_summary.iterrows():
        dname = drow["Dimension"]
        theta_center = float(drow["theta"])
        ts = (theme_summary[theme_summary["Dimension"] == dname]
              .sort_values("Theme"))  # stable order by theme name
        k = len(ts)
        if k == 0:
            continue
        total_span = k * bar_width_deg + (k - 1) * bar_gap_deg
        start = theta_center - total_span / 2.0

        for idx, (_, trow) in enumerate(ts.iterrows()):
            theta_left = start + idx * (bar_width_deg + bar_gap_deg)
            theta_right = theta_left + bar_width_deg

            # Height scaled into compact band beyond the 5-ring:
            height = bar_total_height * (float(trow["theme_mean"]) / max_score)
            r0 = bar_base
            r1 = bar_base + height

            fig.add_trace(go.Scatterpolar(
                theta=[theta_left, theta_right, theta_right, theta_left, theta_left],
                r=[r0, r0, r1, r1, r0],
                mode="lines",
                line=dict(width=0.5, color=trow["bar_color"]),
                fill="toself",
                fillcolor=trow["bar_color"],
                name="Theme avg (0–5)",
                showlegend=False,
                hovertemplate=f"{dname} — {trow['Theme']} ({float(trow['theme_mean']):.2f})<extra></extra>"
            ))

    # Default headline if not supplied
    if title is None and len(dim_summary):
        lowest = dim_summary.sort_values("mean_score").iloc[0]
        title = f"{lowest['Dimension']} is the lowest — focus improvement efforts"

    fig.update_layout(
        title=dict(text=title or "Resilience Maturity — Radar Overview",
                   x=0.5, xanchor="center",
                   font=dict(family="Helvetica, Arial, sans-serif", size=18)),
        showlegend=True,
        legend=dict(orientation="h", x=1, y=-0.1, xanchor="right", yanchor="top"),
        margin=dict(l=40, r=40, t=80, b=80),
        polar=dict(
            radialaxis=dict(
                range=[0, max_score + 1.3],  # gives space for mini bars
                showticklabels=True,
                ticks="outside",
                tickfont=dict(size=10),
                gridcolor="#BFBFBF",
                gridwidth=0.5,
                tickvals=list(range(0, int(max_score) + 1)),
                ticktext=[str(i) for i in range(0, int(max_score) + 1)]
            ),
            angularaxis=dict(
                rotation=90,         # 12 o’clock
                direction="clockwise",
                tickmode="array",
                tickvals=dim_summary["theta"],
                ticktext=dim_summary["Dimension"],
                tickfont=dict(size=10)
            ),
        ),
        template="plotly_white",
    )
    return fig
