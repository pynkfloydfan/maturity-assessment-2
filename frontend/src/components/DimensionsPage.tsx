import { Link } from "react-router-dom";
import Breadcrumb from "./shared/Breadcrumb";
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
}: {
  id: number;
  title: string;
  description?: string | null;
  imageSrc: string;
}) {

  return (
    <Link
      to={`/dimensions/${id}/themes`}
      className="flex w-56 flex-col gap-3 rounded-xl border border-[#e5e8eb] bg-white p-3 text-inherit no-underline shadow-sm transition hover:-translate-y-1 hover:shadow-md"
    >
      <div className="h-40 w-full overflow-hidden rounded-lg bg-[#f5f7fb]">
        <img
          src={imageSrc}
          alt={title}
          className="h-full w-full object-cover"
          onError={(event) => {
            if (event.currentTarget.src !== DIMENSION_PLACEHOLDER) {
              event.currentTarget.src = DIMENSION_PLACEHOLDER;
            }
          }}
        />
      </div>
      <div className="flex flex-col gap-1">
        <h3 className="text-base font-semibold text-[#121417]">{title}</h3>
        <p className="text-sm leading-5 text-[#4d5c6e] line-clamp-3">
          {description ?? "Explore the themes and topics captured within this dimension."}
        </p>
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

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-6 px-6 py-10">
      <Breadcrumb items={[{ label: "Dimensions" }]} />
      <PageHeader dimensionCount={dimensions.length} loading={loading} />
      {loading && <div className="text-sm text-[#61758a]">Loading dimensions…</div>}
      {error && <div className="text-sm text-red-600">{error}</div>}
      {!loading && !error && dimensions.length === 0 && (
        <div className="rounded-lg border border-dashed border-[#d0d7e3] bg-white p-8 text-center text-[#61758a]">
          No framework data found. Seed the database from Settings to begin.
        </div>
      )}
      <div className="flex flex-wrap gap-6">
        {dimensions.map((dimension) => {
          const imageSrc = makeDimensionImagePath(dimension.name);
          return (
            <DimensionTile
              key={dimension.id}
              id={dimension.id}
              title={dimension.name}
              description={dimension.description}
              imageSrc={imageSrc}
            />
          );
        })}
      </div>
    </div>
  );
}
