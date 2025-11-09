import type { ThemeAssessmentBlock } from "../api/types";
import type { ThemeStats } from "../utils/themeStats";

interface ThemeRibbonProps {
  themes: ThemeAssessmentBlock[];
  activeThemeId: number | null;
  statsForTheme: (themeId: number) => ThemeStats;
  onSelect: (themeId: number) => void;
}

export default function ThemeRibbon({ themes, activeThemeId, statsForTheme, onSelect }: ThemeRibbonProps) {
  if (!themes.length) {
    return null;
  }

  return (
    <div className="theme-ribbon" role="tablist" aria-label="Theme selector">
      {themes.map((theme) => {
        const stats = statsForTheme(theme.id);
        const progressPercent = stats.total ? Math.round((stats.done / stats.total) * 100) : 0;
        const isActive = theme.id === activeThemeId;
        return (
          <button
            key={theme.id}
            type="button"
            className={`theme-tile${isActive ? " theme-tile--active" : ""}`}
            onClick={() => onSelect(theme.id)}
            aria-pressed={isActive}
          >
            <div className="theme-tile__title">{theme.name}</div>
            {theme.description && (
              <div className="theme-tile__description">{theme.description}</div>
            )}
            <div className="theme-tile__metrics">
              <div className="theme-tile__progress">
                <div className="theme-tile__progress-bar" style={{ width: `${progressPercent}%` }} />
              </div>
              <span className="theme-tile__count">
                {stats.done}/{stats.total}
              </span>
              <span className="theme-tile__delta">Δ {stats.gap.toFixed(1)}</span>
            </div>
          </button>
        );
      })}
    </div>
  );
}
