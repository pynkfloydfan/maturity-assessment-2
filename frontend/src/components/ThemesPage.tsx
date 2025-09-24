import { Link, useParams } from "react-router-dom";
import Breadcrumb from "./shared/Breadcrumb";
import { useDimensions } from "../hooks/useDimensions";
import { useThemes } from "../hooks/useThemes";

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
}: {
  dimensionId: number;
  themeId: number;
  title: string;
  description?: string | null;
  category?: string | null;
  imageSrc: string;
  fallbackImage: string;
}) {
  return (
    <Link
      to={`/dimensions/${dimensionId}/themes/${themeId}/topics`}
      className="flex h-full flex-col rounded-2xl border border-[#d7deea] bg-white p-6 text-inherit no-underline shadow-sm transition-transform hover:-translate-y-1 hover:shadow-lg"
    >
      <div className="relative mb-4 h-44 w-full overflow-hidden rounded-2xl bg-[#f5f7fb]">
        <img
          src={imageSrc}
          alt={title}
          className="h-full w-full object-cover"
          onError={(event) => {
            if (event.currentTarget.src !== fallbackImage) {
              event.currentTarget.src = fallbackImage;
            } else if (fallbackImage !== DIMENSION_PLACEHOLDER) {
              event.currentTarget.src = DIMENSION_PLACEHOLDER;
            }
          }}
        />
      </div>
      <div className="flex flex-1 flex-col gap-2">
        <span className="text-xs uppercase tracking-wide text-[#61758a]">{category ?? "Theme"}</span>
        <h3 className="text-lg font-semibold text-[#121417] leading-tight">{title}</h3>
        <p className="text-sm leading-6 text-[#4d5c6e] line-clamp-4">
          {description ?? "Review the topics and capture ratings for this theme."}
        </p>
      </div>
    </Link>
  );
}

export default function ThemesPage() {
  const params = useParams<{ dimensionId: string }>();
  const dimensionId = params.dimensionId ? Number.parseInt(params.dimensionId, 10) : NaN;
  const { dimensions } = useDimensions();
  const { themes, loading, error } = useThemes(Number.isNaN(dimensionId) ? null : dimensionId);

  const dimension = dimensions.find((item) => item.id === dimensionId);

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

  const breadcrumbItems = [
    { label: "Dimensions", path: "/" },
    { label: dimension.name },
  ];

  return (
    <div className="page-section">
      <Breadcrumb items={breadcrumbItems} />
      <div className="page-hero">
        <div className="pill">{dimension.name}</div>
        <div>
          <h1>Navigate themes &amp; prioritise focus areas</h1>
          <p>
            Each theme explores a focused capability within {dimension.name}. Choose a tile to review
            descriptive guidance and capture topic-level ratings with confidence.
          </p>
        </div>
        <div className="status-card">
          <div className="status-item">
            <div className="status-label">Themes</div>
            <div className="status-value">{loading ? "–" : themes.length}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Dimension</div>
            <div className="status-value">{dimension.name}</div>
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
          const themeImage = `/static/images/themes/${dimensionSlug}/${themeSlug}.png`;
          const fallbackImage = `/static/images/dimensions/${dimensionSlug}.png`;

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
            />
          );
        })}
      </div>
    </div>
  );
}
