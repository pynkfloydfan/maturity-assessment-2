import numpy as np
import pandas as pd
import plotly.graph_objects as go


# --- Color interpolation helpers (kept module-level for reuse) ---
def hex_to_rgb(h: str) -> tuple[int, int, int]:
    h = h.lstrip("#")
    return (
        int(h[0:2], 16),
        int(h[2:4], 16),
        int(h[4:6], 16),
    )


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    r, g, b = rgb
    return f"#{r:02X}{g:02X}{b:02X}"


def lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


# Default stops (unchanged from your original)
# 0:#D73027, 2:#FC8D59, 3:#FEE08B, 4:#91CF60, 5:#1A9850
DEFAULT_STOPS: list[tuple[float, str]] = [
    (1.0, "#D73027"),
    (2.0, "#D78827"),
    (3.0, "#FEE08B"),
    (4.0, "#27D730"),
    (5.0, "#3027D7"),
]


def gradient_color(value: float, stops: list[tuple[float, str]] = DEFAULT_STOPS) -> str:
    """Piecewise-linear interpolation across hex color stops."""
    v = float(value)
    if v <= stops[0][0]:
        return stops[0][1]
    if v >= stops[-1][0]:
        return stops[-1][1]
    for i in range(len(stops) - 1):
        v0, c0 = stops[i]
        v1, c1 = stops[i + 1]
        if v0 <= v <= v1:
            t = 0.0 if v1 == v0 else (v - v0) / (v1 - v0)
            r0, g0, b0 = hex_to_rgb(c0)
            r1, g1, b1 = hex_to_rgb(c1)
            r = int(round(lerp(r0, r1, t)))
            g = int(round(lerp(g0, g1, t)))
            b = int(round(lerp(b0, b1, t)))
            return rgb_to_hex((r, g, b))
    return stops[-1][1]


def _add_theme_bar(fig, *, theta_left, theta_right, r0, r1, color, theme_name, theme_mean):
    # visible filled bar
    fig.add_trace(
        go.Scatterpolar(
            theta=[theta_left, theta_right, theta_right, theta_left, theta_left],
            r=[r0, r0, r1, r1, r0],
            mode="lines",
            line=dict(width=0.5, color=color),
            fill="toself",
            fillcolor=color,
            name="",
            showlegend=False,
            hoverinfo="skip",
        )
    )
    # invisible hover target at center
    theta_mid = (theta_left + theta_right) / 2.0
    r_mid = (r0 + r1) / 2.0
    fig.add_trace(
        go.Scatterpolar(
            theta=[theta_mid],
            r=[r_mid],
            mode="markers",
            marker=dict(size=32, color="rgba(0,0,0,0)"),
            name="",
            showlegend=False,
            hovertemplate=f"{theme_name} - {theme_mean:.2f}<extra></extra>",
        )
    )


def make_resilience_radar_with_theme_bars(
    scores: pd.DataFrame,
    dimension_order: list[str] | None = None,
    title: str | None = None,
    max_score: float = 5.0,
    bar_base: float = 5.35,  # start of mini bars (just beyond the 5-ring)
    bar_total_height: float = 0.8,  # visual height representing max_score
    bar_width_deg: float = 1.4,  # angular width of each theme bar
    bar_gap_deg: float = 0.6,  # angular gap between theme bars
) -> go.Figure:
    """
    Build a radar chart (one spoke per Dimension) with grouped mini bars at each spoke tip.
    Each mini bar corresponds to a Theme within that Dimension, with bar height = avg Theme score.
    Bars are drawn just beyond the 5-ring to keep the radar readable.

    Parameters match the original; visual output is intentionally identical.
    """
    # -------- input validation --------
    required_cols = {"Dimension", "Theme", "Question", "Score"}
    missing = required_cols - set(scores.columns)
    if missing:
        raise ValueError(f"Scores DataFrame missing required columns: {sorted(missing)}")
    if not np.issubdtype(scores["Score"].dtype, np.number):
        raise TypeError("Column 'Score' must be numeric.")

    # Clamp scores to [0, max_score] defensively (does not change typical inputs)
    scores = scores.copy()
    scores["Score"] = scores["Score"].astype(float).clip(lower=0.0, upper=float(max_score))

    # -------- summaries --------
    dim_summary = scores.groupby("Dimension", as_index=False).agg(mean_score=("Score", "mean"))
    theme_summary = scores.groupby(["Dimension", "Theme"], as_index=False).agg(
        theme_mean=("Score", "mean")
    )

    # -------- dimension order & angles --------
    if dimension_order is None:
        # Preserve first-appearance order for Dimensions
        dims = list(pd.unique(scores["Dimension"]))
    else:
        dims = list(dimension_order)
        # sanity: ensure all provided dims exist in data
        unknown = set(dims) - set(dim_summary["Dimension"])
        if unknown:
            raise ValueError(f"dimension_order includes unknown dimensions: {sorted(unknown)}")

    # Equally spaced angles (degrees), starting at 12 o'clock and clockwise in layout
    angles = np.linspace(0.0, 360.0, len(dims), endpoint=False)
    angle_map = pd.DataFrame({"Dimension": dims, "theta": angles})

    dim_summary = dim_summary.merge(angle_map, on="Dimension", how="right")
    theme_summary = theme_summary.merge(angle_map, on="Dimension", how="left")

    # -------- colours (unchanged behaviour) --------
    dim_summary["mean_color"] = dim_summary["mean_score"].apply(gradient_color)
    theme_summary["bar_color"] = theme_summary["theme_mean"].apply(gradient_color)

    # -------- figure --------
    fig = go.Figure()

    # Radar polygon (connect dimension means) — keep the subtle fill as in original
    r_vals = dim_summary["mean_score"].tolist()
    theta_vals = dim_summary["theta"].tolist()
    if len(r_vals) >= 1:
        r_loop = r_vals + [r_vals[0]]
        theta_loop = theta_vals + [theta_vals[0]]
        fig.add_trace(
            go.Scatterpolar(
                r=r_loop,
                theta=theta_loop,
                mode="lines",
                line=dict(color="#666666", width=1.5),
                fill="toself",
                fillcolor="rgba(0,0,0,0.08)",
                name="Mean Score (0–5)",
                hoverinfo="skip",
            )
        )

    # Mean markers per dimension (colour by gradient)
    fig.add_trace(
        go.Scatterpolar(
            r=dim_summary["mean_score"],
            theta=dim_summary["theta"],
            mode="markers+text",
            marker=dict(size=10, color=dim_summary["mean_color"]),
            text=[f"{m:.1f}" for m in dim_summary["mean_score"]],
            textposition="top center",
            name="Mean by Dimension",
            hovertemplate="<b>%{customdata[0]}</b><br>Mean: %{customdata[1]:.2f}<extra></extra>",
            customdata=np.stack([dim_summary["Dimension"], dim_summary["mean_score"]], axis=1),
        )
    )

    # Grouped mini bars at spoke tip (one bar per Theme) — draw as polar rectangles
    for _, drow in dim_summary.iterrows():
        dname = drow["Dimension"]
        theta_center = float(drow["theta"])
        # Stable order by theme name
        ts = theme_summary[theme_summary["Dimension"] == dname].sort_values("Theme")
        k = int(ts.shape[0])
        if k == 0:
            continue

        total_span = k * bar_width_deg + (k - 1) * bar_gap_deg
        start = theta_center - total_span / 2.0

        for idx, (_, trow) in enumerate(ts.iterrows()):
            theta_left = start + idx * (bar_width_deg + bar_gap_deg)
            theta_right = theta_left + bar_width_deg

            # Height scaled into compact band beyond the 5-ring:
            theme_name = str(trow["Theme"])
            theme_mean = float(trow["theme_mean"])
            height = float(bar_total_height) * (theme_mean / float(max_score))
            height = max(0.0, height)  # guard

            r0 = float(bar_base)
            r1 = float(bar_base) + height

            # Draw a filled polar rectangle (as a closed polygon)
            _add_theme_bar(
                fig,
                theta_left=theta_left,
                theta_right=theta_right,
                r0=r0,
                r1=r1,
                color=trow["bar_color"],
                theme_name=theme_name,
                theme_mean=theme_mean,
            )

    # Default headline if not supplied (unchanged)
    if title is None and len(dim_summary):
        lowest = dim_summary.sort_values("mean_score").iloc[0]
        title = f"{lowest['Dimension']} is the lowest — focus improvement efforts"

    fig.update_layout(
        title=dict(
            text=title or "Resilience Maturity — Radar Overview",
            x=0.5,
            xanchor="center",
            font=dict(family="Helvetica, Arial, sans-serif", size=18),
        ),
        showlegend=True,
        legend=dict(orientation="h", x=1, y=-0.1, xanchor="right", yanchor="top"),
        margin=dict(l=40, r=40, t=80, b=80),
        polar=dict(
            radialaxis=dict(
                range=[0, float(max_score) + 1.3],  # leave space for mini bars
                showticklabels=True,
                ticks="outside",
                tickfont=dict(size=10),
                gridcolor="#BFBFBF",
                gridwidth=0.5,
                tickvals=list(range(0, int(max_score) + 1)),
                ticktext=[str(i) for i in range(0, int(max_score) + 1)],
            ),
            angularaxis=dict(
                rotation=90,  # 12 o’clock
                direction="clockwise",
                tickmode="array",
                tickvals=dim_summary["theta"],
                ticktext=dim_summary["Dimension"],
                tickfont=dict(size=20),
            ),
        ),
        template="plotly_white",
    )
    fig.update_layout(height=560)
    return fig
