import { useMemo } from "react";
import { Link } from "react-router-dom";
import { Grid3x3Icon, ImageIcon, ListChecksIcon, SparklesIcon } from "../icons";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";
import { useDimensions } from "../hooks/useDimensions";

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

function makeDimensionImagePath(name: string): string {
  const slug = DIMENSION_SLUGS[name] ?? name.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  return `/static/images/dimensions/${slug}.png`;
}

function DimensionTile({
  id,
  title,
  description,
  imageSrc,
  themeCount,
  topicCount,
}: {
  id: number;
  title: string;
  description?: string | null;
  imageSrc: string;
  themeCount?: number | null;
  topicCount?: number | null;
}) {
  return (
    <Link
      to={`/dimensions/${id}/themes`}
      className="tile-card"
    >
      <div className="tile-card__media">
        <img
          src={imageSrc}
          alt={title}
          onError={(event) => {
            if (event.currentTarget.src !== DIMENSION_PLACEHOLDER) {
              event.currentTarget.src = DIMENSION_PLACEHOLDER;
            }
          }}
        />
      </div>
      <div className="tile-card__content">
        <h3 className="tile-card__title">{title}</h3>
        <p className="tile-card__description line-clamp-4">
          {description ?? "Explore the themes and topics captured within this dimension."}
        </p>
        <div className="tile-card__meta">
          <span className="badge-soft">
            <SparklesIcon />
            {`${themeCount ?? 0} themes`}
          </span>
          <span className="badge-soft">
            <ListChecksIcon />
            {`${topicCount ?? 0} topics`}
          </span>
        </div>
      </div>
    </Link>
  );
}

function PageHeader({ dimensionCount, loading }: { dimensionCount: number; loading: boolean }) {
  const countLabel = loading ? "–" : String(dimensionCount);
  return (
    <header className="mb-8">
      <div className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold text-[#121417]">Dimensions</h1>
        <p className="max-w-3xl text-base leading-6 text-[#4d5c6e]">
          Dimensions are the pillars of the resilience framework. Select a dimension to drill into its themes and capture topic-level assessments using the guidance sourced from the latest operational resilience blueprint.
        </p>
        <span className="text-sm text-[#61758a]">{countLabel} dimensions available</span>
      </div>
    </header>
  );
}

export default function DimensionsPage() {
  const { dimensions, loading, error } = useDimensions();

  const dimensionCount = dimensions.length;
  const themeCount = dimensions.reduce((acc, item) => acc + (item.theme_count ?? 0), 0);

  const breadcrumbItems = useMemo(() => [{ label: "Dimensions" }], []);
  usePageBreadcrumb(breadcrumbItems);

  return (
    <div className="page-section">
      <div className="page-hero">
      <div className="pill">Dimension Library</div>
      <div>
        <h1>Explore your resilience landscape</h1>
        <p>
            Navigate every dimension of the operational resilience framework with richer guidance,
            imagery, and at-a-glance insights. Select a card to drill into themes and capture
            structured assessments.
          </p>
        </div>
        <div className="status-card">
          <div className="status-item">
            <span className="status-item__icon">
              <Grid3x3Icon />
            </span>
            <div className="status-label">Dimensions</div>
            <div className="status-value">{loading ? "–" : dimensionCount}</div>
          </div>
          <div className="status-item">
            <span className="status-item__icon">
              <SparklesIcon />
            </span>
            <div className="status-label">Themes</div>
            <div className="status-value">{loading ? "–" : themeCount}</div>
          </div>
          <div className="status-item">
            <span className="status-item__icon">
              <ImageIcon />
            </span>
            <div className="status-label">Imagery</div>
            <div className="status-value">Curated</div>
          </div>
        </div>
      </div>

      {error && <div className="info-banner error">{error}</div>}
      {loading && <div className="info-banner">Loading dimensions…</div>}
      {!loading && !error && dimensionCount === 0 && (
        <div className="card">
          <h2 className="settings-heading">No data found</h2>
          <p className="settings-subcopy">
            Seed the database from the Settings page to load the enhanced operational resilience
            framework.
          </p>
        </div>
      )}

      <div className="dimensions-grid">
        {dimensions.map((dimension) => {
          const imageSrc = makeDimensionImagePath(dimension.name);
          return (
            <DimensionTile
              key={dimension.id}
              id={dimension.id}
              title={dimension.name}
              description={dimension.description}
              imageSrc={imageSrc}
              themeCount={dimension.theme_count}
              topicCount={dimension.topic_count}
            />
          );
        })}
      </div>
    </div>
  );
}
