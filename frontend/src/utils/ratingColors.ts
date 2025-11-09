import type { CSSProperties } from "react";

const DEFAULT_RATING_COLORS: Record<number, string> = {
  1: "#D73027",
  2: "#D78827",
  3: "#F9D23C",
  4: "#27D730",
  5: "#3027D7",
};

export function getRatingColor(level?: number | null): string | null {
  if (typeof level !== "number" || level <= 0) {
    return null;
  }
  const rounded = Math.max(1, Math.min(5, Math.round(level)));
  return DEFAULT_RATING_COLORS[rounded] ?? null;
}

export function getRatingChipStyle(level?: number | null): CSSProperties | undefined {
  const color = getRatingColor(level);
  if (!color) return undefined;
  return {
    backgroundColor: color,
    borderColor: color,
    color: getReadableTextColor(color),
  };
}

export function getGradientStyle(from?: number | null, to?: number | null): CSSProperties | undefined {
  const start = getRatingColor(from);
  const end = getRatingColor(to);
  if (!start && !end) return undefined;
  if (start && end && start !== end) {
    return {
      background: `linear-gradient(90deg, ${start}, ${end})`,
      color: "#fff",
      borderColor: "transparent",
    };
  }
  const color = start ?? end;
  return color
    ? {
        backgroundColor: color,
        borderColor: color,
        color: getReadableTextColor(color),
      }
    : undefined;
}

function getReadableTextColor(color: string): string {
  const rgb = hexToRgb(color);
  if (!rgb) return "#fff";
  const [r, g, b] = rgb.map((n) => n / 255);
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
  return luminance > 0.65 ? "#0f172a" : "#fff";
}

function hexToRgb(color: string): [number, number, number] | null {
  const cleaned = color.replace("#", "");
  if (cleaned.length !== 6) return null;
  const r = Number.parseInt(cleaned.slice(0, 2), 16);
  const g = Number.parseInt(cleaned.slice(2, 4), 16);
  const b = Number.parseInt(cleaned.slice(4, 6), 16);
  if (Number.isNaN(r) || Number.isNaN(g) || Number.isNaN(b)) return null;
  return [r, g, b];
}
