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
      className="flex w-56 flex-col gap-3 rounded-xl border border-[#e5e8eb] bg-white p-3 text-inherit no-underline shadow-sm transition hover:-translate-y-1 hover:shadow-md"
    >
      <div className="h-36 w-full overflow-hidden rounded-lg bg-[#f3f5f9]">
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
      <div className="flex flex-col gap-1">
        <span className="text-xs uppercase tracking-wide text-[#61758a]">{category ?? "Theme"}</span>
        <h3 className="text-base font-semibold text-[#121417]">{title}</h3>
        <p className="text-sm leading-5 text-[#4d5c6e] line-clamp-3">
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
    return (
      <div className="mx-auto max-w-4xl px-6 py-10 text-[#61758a]">
        Invalid dimension identifier provided.
      </div>
    );
  }

  if (!dimension) {
    return (
      <div className="mx-auto max-w-4xl px-6 py-10">
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-10 text-center">
          <h2 className="mb-2 text-xl font-semibold text-[#121417]">Dimension not found</h2>
          <p className="mb-4 text-[#61758a]">The requested dimension is not available. Please return to the dimensions overview.</p>
          <Link to="/" className="text-[#0d80f2] underline">Back to Dimensions</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <Breadcrumb items={[{ label: "Dimensions", path: "/" }, { label: dimension.name }]} />
      <header className="flex flex-col gap-2">
        <h1 className="text-3xl font-semibold text-[#121417]">{dimension.name} · Themes</h1>
        <p className="max-w-3xl text-base leading-6 text-[#4d5c6e]">
          Select a theme to review its topics and update assessment ratings. The descriptive copy is sourced from the enhanced resilience framework.
        </p>
        <span className="text-sm text-[#61758a]">{themes.length} themes</span>
      </header>
      {loading && <div className="text-sm text-[#61758a]">Loading themes…</div>}
      {error && <div className="text-sm text-red-600">{error}</div>}
      {!loading && !error && themes.length === 0 && (
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-8 text-center text-[#61758a]">
          No themes found for this dimension.
        </div>
      )}
      <div className="flex flex-wrap gap-6">
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
