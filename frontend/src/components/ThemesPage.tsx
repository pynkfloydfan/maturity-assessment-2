import { useMemo } from "react";
import { Link, useParams } from "react-router-dom";
import { Grid3x3Icon, ImageIcon, ListChecksIcon, SparklesIcon } from "../icons";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import { useDimensions } from "../hooks/useDimensions";
import { useThemes } from "../hooks/useThemes";
import { useAcronymHighlighter } from "../hooks/useAcronymHighlighter";

const DIMENSION_SLUGS: Record<string, string> = {
  "Governance & Leadership": "governance-leadership",
  "Risk Assessment & Management": "risk-assessment-management",
  "BC & DR Planning": "bc-dr-planning",
  "Process & Dependency Mapping": "process-dependency-mapping",
  "IT & Cyber Resilience": "it-cyber-resilience",
  "Crisis Comms & Incident Mgmt": "crisis-comms-incident-mgmt",
  "Third-Party Resilience": "third-party-resilience",
  "Culture & Human Factors": "culture-human-factors",
  "Regulatory Compliance & Resolvability": "regulatory-compliance-resolvability",
};

const DIMENSION_PLACEHOLDER = "/static/images/dimensions/default.png";

function slugify(value: string): string {
  return value
    .toLowerCase()
    .replace(/&/g, "and")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-+|-+$/g, "");
}

function ThemeTile({
  dimensionId,
  themeId,
  title,
  description,
  category,
  imageSrc,
  fallbackImage,
  topicCount,
}: {
  dimensionId: number;
  themeId: number;
  title: string;
  description?: string | null;
  category?: string | null;
  imageSrc: string;
  fallbackImage: string;
  topicCount?: number | null;
}) {
  const highlight = useAcronymHighlighter();
  return (
    <Link
      to={`/dimensions/${dimensionId}/themes/${themeId}/topics`}
      className="tile-card"
    >
      <div className="tile-card__media">
        <img
          src={imageSrc}
          alt={title}
          onError={(event) => {
            if (event.currentTarget.src !== fallbackImage) {
              event.currentTarget.src = fallbackImage;
            } else if (fallbackImage !== DIMENSION_PLACEHOLDER) {
              event.currentTarget.src = DIMENSION_PLACEHOLDER;
            }
          }}
        />
        <span className="tile-card__badge">
          <SparklesIcon />
          {category ?? "Theme"}
        </span>
      </div>
      <div className="tile-card__content">
        <h3 className="tile-card__title">{highlight(title)}</h3>
        <p className="tile-card__description line-clamp-4">
          {highlight(description ?? "Review the topics and capture ratings for this theme.")}
        </p>
        <div className="tile-card__meta">
          <span className="badge-soft">
            <ListChecksIcon />
            {topicCount ?? 0} topics
          </span>
          <span className="badge-soft">
            <ImageIcon />
            Shared art
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function ThemesPage() {
  const params = useParams<{ dimensionId: string }>();
  const dimensionId = params.dimensionId ? Number.parseInt(params.dimensionId, 10) : NaN;
  const { dimensions } = useDimensions();
  const { themes, loading, error } = useThemes(Number.isNaN(dimensionId) ? null : dimensionId);
  const highlight = useAcronymHighlighter();

  const dimension = dimensions.find((item) => item.id === dimensionId);

  const breadcrumbItems = useMemo(() => {
    return [{ label: "Dimensions", path: "/" }, dimension ? { label: dimension.name } : null].filter(
      Boolean,
    ) as { label: string; path?: string }[];
  }, [dimension]);
  usePageBreadcrumb(breadcrumbItems);

  if (!dimensionId || Number.isNaN(dimensionId)) {
    return <div className="info-banner error">Invalid dimension identifier provided.</div>;
  }

  if (!dimension) {
    return (
      <div className="card">
        <h2 className="settings-heading">Dimension not found</h2>
        <p className="settings-subcopy">
          The requested dimension is not available. Please return to the Dimensions overview.
        </p>
        <Link to="/" className="muted-link">Back to Dimensions</Link>
      </div>
    );
  }

  return (
    <div className="page-section">
      <div className="page-hero">
        <div className="pill">{highlight(dimension.name)}</div>
        <div>
          <h1>{highlight(dimension.name)}</h1>
          {dimension.description && <p>{highlight(dimension.description)}</p>}
          <p>
            Each theme explores a focused capability within {highlight(dimension.name)}. Choose a tile to review
            descriptive guidance and capture topic-level ratings with confidence.
          </p>
        </div>
        <div className="status-card">
          <div className="status-item">
            <span className="status-item__icon">
              <SparklesIcon />
            </span>
            <div className="status-label">Themes</div>
            <div className="status-value">{loading ? "–" : themes.length}</div>
          </div>
          <div className="status-item">
            <span className="status-item__icon">
              <Grid3x3Icon />
            </span>
            <div className="status-label">Dimension</div>
            <div className="status-value">{highlight(dimension.name)}</div>
          </div>
        </div>
      </div>

      {error && <div className="info-banner error">{error}</div>}
      {loading && <div className="info-banner">Loading themes…</div>}
      {!loading && !error && themes.length === 0 && (
        <div className="card">
          <h2 className="settings-heading">No themes available</h2>
          <p className="settings-subcopy">
            Seed the dataset or refresh the framework to populate the theme catalogue.
          </p>
        </div>
      )}

      <div className="themes-grid">
        {themes.map((theme) => {
          const dimensionSlug = DIMENSION_SLUGS[dimension.name] ?? slugify(dimension.name);
          const themeSlug = slugify(theme.name);
          const themeImage = `/static/images/themes/${dimensionSlug}/${themeSlug}.jpg`;
          const fallbackImage = `/static/images/dimensions/${dimensionSlug}.jpg`;

          return (
            <ThemeTile
              key={theme.id}
              dimensionId={dimension.id}
              themeId={theme.id}
              title={theme.name}
              description={theme.description}
              category={theme.category}
              imageSrc={themeImage}
              fallbackImage={fallbackImage}
              topicCount={theme.topic_count}
            />
          );
        })}
      </div>
    </div>
  );
}
