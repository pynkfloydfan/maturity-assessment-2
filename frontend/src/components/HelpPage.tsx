import { Fragment, ReactNode } from "react";

interface HelpSection { id: string; title: string; content: ReactNode; }

const sections: HelpSection[] = [
  {
    id: "introduction",
    title: "Introduction",
    content: (
      <Fragment>
        <p>
          The Operational Resilience Maturity Assessment blends a FastAPI backend, React/Vite frontend,
          and SQL database (SQLite by default, MySQL optional) to let teams capture, analyse, and report on
          CMMI-aligned assessments. This guide distils the platform capabilities into user-friendly steps
          for administrators and assessors.
        </p>
      </Fragment>
    ),
  },
  {
    id: "quick-start-checklist",
    title: "Quick Start Checklist",
    content: (
      <ol className="help-list ordered">
        <li>
          <strong>Install dependencies:</strong> run <code>poetry install</code> for backend tooling and {' '}<code>npm install</code> inside <code>frontend/</code> for the React bundle.
        </li>
        <li>
          <strong>Configure the database:</strong> use <em>Settings → Database configuration</em> or
          provide the <code>DB_</code> environment variables listed below.
        </li>
        <li>
          <strong>Initialise the schema:</strong> click <em>Initialise tables</em> or run {' '}<code>poetry run alembic upgrade head</code> to apply migrations.
        </li>
        <li>
          <strong>Seed the enhanced dataset:</strong> trigger seeding from Settings or run {' '}<code>poetry run seed-database</code> (defaults to {' '}<code>app/source_data/Maturity_Assessment_Data.xlsx</code>).
        </li>
        <li>
          <strong>Create a session:</strong> add at least one session in Settings so dashboards have
          context.
        </li>
        <li>
          <strong>Capture ratings:</strong> enter data via the assessment pages or import from Excel.
        </li>
        <li>
          <strong>Review dashboards:</strong> open the Dashboard tab and export JSON/XLSX when needed.
        </li>
      </ol>
    ),
  },
  {
    id: "application-navigation",
    title: "Application Navigation",
    content: (
      <ul className="help-list">
        <li>
          <strong>Header:</strong> choose the active session and access primary routes.
        </li>
        <li>
          <strong>Dashboard:</strong> visualises maturity heatmap tiles, radar plot, and summary metrics.
        </li>
        <li>
          <strong>Dimensions/Themes/Topics:</strong> drill down to capture ratings and guidance comments.
        </li>
        <li>
          <strong>Settings:</strong> administrative hub for database setup, seeding, uploads, and session
          management.
        </li>
      </ul>
    ),
  },
  {
    id: "working-with-sessions",
    title: "Working with Sessions",
    content: (
      <Fragment>
        <h3>Create sessions</h3>
        <p>
          Navigate to <em>Settings → Sessions</em>. Provide a name (assessor, organisation, and notes are
          optional) and submit. The list refreshes automatically.
        </p>
        <h3>Select sessions</h3>
        <p>
          Use the header dropdown. The dashboard banner shows the active session number (e.g.,
          <code>#12</code>).
        </p>
        <h3>Combine sessions</h3>
        <p>
          Multi-select existing sessions, choose a master name, and click <em>Combine selected</em>. Ratings
          are averaged (excluding N/A) and stored in a new session.
        </p>
        <h3>Edit ratings</h3>
        <p>
          Update values directly in the assessment pages or via bulk Excel upload described below.
        </p>
      </Fragment>
    ),
  },
  {
    id: "dashboard-insights",
    title: "Dashboard Insights",
    content: (
      <Fragment>
        <p>
          The dashboard pulls data from <code>/api/sessions/{'{id}'}/dashboard</code> and {' '}<code>/api/sessions/{'{id}'}/dashboard/figures</code> to provide a holistic view.
        </p>
        <ul className="help-list">
          <li>
            <strong>Maturity heatmap:</strong> gradient tiles per dimension showing average score,
            coverage, and status messaging.
          </li>
          <li>
            <strong>Radar plot:</strong> Plotly chart (see <code>resilience_radar.py</code>) with grouped
            theme mini-bars for visual comparison.
          </li>
          <li>
            <strong>Status cards:</strong> top-level metrics summarising session ID, total tiles, and mean
            coverage/score.
          </li>
        </ul>
      </Fragment>
    ),
  },
  {
    id: "database-configuration",
    title: "Database Configuration",
    content: (
      <Fragment>
        <p>
          Runtime settings derive from <code>app/infrastructure/config.py</code>. Configure them via the
          Settings page or environment variables.
        </p>
        <table className="help-table">
          <thead>
            <tr>
              <th>Variable</th>
              <th>Purpose</th>
              <th>Notes</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>DB_BACKEND</code></td>
              <td>Selects <code>sqlite</code> (default) or <code>mysql</code></td>
              <td>Controls which settings block applies</td>
            </tr>
            <tr>
              <td><code>DB_SQLITE_PATH</code></td>
              <td>SQLite database path</td>
              <td>Defaults to <code>./resilience.db</code></td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_HOST</code></td>
              <td>MySQL hostname</td>
              <td>Required for MySQL deployments</td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_PORT</code></td>
              <td>MySQL port</td>
              <td>Default <code>3306</code></td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_USER</code></td>
              <td>MySQL username</td>
              <td>Required for MySQL deployments</td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_PASSWORD</code></td>
              <td>Password</td>
              <td>Optional but generally needed</td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_DATABASE</code></td>
              <td>Database name</td>
              <td>Required for MySQL deployments</td>
            </tr>
            <tr>
              <td><code>DB_MYSQL_CHARSET</code></td>
              <td>Character set</td>
              <td>Defaults to <code>utf8mb4</code></td>
            </tr>
            <tr>
              <td>
                <code>DB_POOL_PRE_PING</code>, <code>DB_POOL_RECYCLE</code>, <code>DB_ECHO</code>
              </td>
              <td>Connection tuning flags</td>
              <td>Optional overrides</td>
            </tr>
          </tbody>
        </table>
        <p>
          The Settings page exposes <em>Save configuration</em>, <em>Initialise tables</em>, and
          <em>Seed from Excel</em> actions that wrap these configuration hooks.
        </p>
      </Fragment>
    ),
  },
  {
    id: "seeding--maintaining-data",
    title: "Seeding & Maintaining Data",
    content: (
      <ul className="help-list">
        <li>
          The canonical workbook is <code>app/source_data/Maturity_Assessment_Data.xlsx</code>.
        </li>
        <li>
          Seeding populates dimensions, themes, topics, rating scales, guidance, and explanations (see {' '}<code>scripts/seed_dataset.py</code>).
        </li>
        <li>
          Re-running the seed script updates descriptions and replaces per-topic guidance while keeping IDs
          consistent.
        </li>
        <li>
          Use <em>Refresh sessions</em> in Settings to reload the session list after seeding.
        </li>
      </ul>
    ),
  },
  {
    id: "uploading-assessments-from-excel",
    title: "Uploading Assessments from Excel",
    content: (
      <Fragment>
        <h3>Template</h3>
        <p>
          Download <code>/static/templates/assessment_upload_template.xlsx</code>. It mirrors the export
          format with a single sheet named <em>Assessment</em>.
        </p>
        <h3>Column expectations</h3>
        <table className="help-table">
          <thead>
            <tr>
              <th>Column</th>
              <th>Required?</th>
              <th>Behaviour</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><code>TopicID</code></td>
              <td>Yes</td>
              <td>Must map to an existing topic; missing/invalid values trigger errors.</td>
            </tr>
            <tr>
              <td><code>Rating</code></td>
              <td>Optional</td>
              <td>Parsed as integers 1–5; invalid values trigger errors.</td>
            </tr>
            <tr>
              <td><code>ComputedScore</code></td>
              <td>Optional</td>
              <td>Parsed as decimal numbers; ignored if blank.</td>
            </tr>
            <tr>
              <td><code>N/A</code></td>
              <td>Optional</td>
              <td>Boolean (<code>true</code>, <code>yes</code>, <code>1</code>, etc.); when true ignore rating.</td>
            </tr>
            <tr>
              <td><code>Comment</code></td>
              <td>Optional</td>
              <td>Trimmed text; empty strings become <code>null</code>.</td>
            </tr>
            <tr>
              <td>Other columns</td>
              <td>No</td>
              <td>Ignored by the importer but useful for context.</td>
            </tr>
          </tbody>
        </table>
        <h3>Upload steps</h3>
        <ol className="help-list ordered">
          <li>Open <em>Settings → Upload assessment</em>.</li>
          <li>Select the target session (defaults to the newest session on load).</li>
          <li>Choose your Excel file (<code>.xlsx</code> recommended).</li>
          <li>Click <em>Upload assessment</em>. The button is enabled once a file is selected.</li>
          <li>
            Success returns a message such as “Imported X entries.” Validation errors list the row and
            reason; nothing is committed when errors occur.
          </li>
        </ol>
        <p>
          Only rows with a meaningful update (rating, computed score, comment, or N/A flag) are applied. The
          importer upserts entries using the same validation as the API.
        </p>
      </Fragment>
    ),
  },
  {
    id: "exporting-assessment-results",
    title: "Exporting Assessment Results",
    content: (
      <ul className="help-list">
        <li>
          <strong>JSON export:</strong> <code>/api/sessions/{'{id}'}/exports/json</code> returns topics and
          entries arrays mirroring the dashboard payload.
        </li>
        <li>
          <strong>XLSX export:</strong> <code>/api/sessions/{'{id}'}/exports/xlsx</code> serves a single-sheet
          workbook named <em>Assessment</em> with topics joined on <code>TopicID</code>.
        </li>
        <li>
          Both actions are available from the dashboard toolbar and can be scripted against the same
          endpoints.
        </li>
      </ul>
    ),
  },
  {
    id: "command-line-utilities",
    title: "Command-Line Utilities",
    content: (
      <ul className="help-list">
        <li>
          <code>poetry run seed-database</code>: wraps <code>scripts/seed_dataset.py</code>; accepts backend
          flags, SQLite path, and MySQL credentials (aliases <code>--mysql-database</code> / <code>--mysql-db</code>).
        </li>
        <li>
          <code>poetry run server</code>: runs <code>scripts/run_server.py</code>, ensuring the frontend build
          exists before launching Uvicorn in reload mode.
        </li>
        <li>
          <code>poetry run uvicorn app.web.main:app --reload</code>: start the API directly when you manage the
          frontend build manually.
        </li>
      </ul>
    ),
  },
  {
    id: "troubleshooting--faqs",
    title: "Troubleshooting & FAQs",
    content: (
      <div className="help-faq">
        <h3>“Select a session” banner</h3>
        <p>No active session is selected. Pick one from the header dropdown or create a session.</p>
        <h3>Seeding errors</h3>
        <p>
          Review the seeding output in Settings. Ensure environment variables use the <code>DB_</code> prefixes.
        </p>
        <h3>Excel import validation errors</h3>
        <p>
          Confirm every row has a valid <code>TopicID</code> and that ratings are integers. Error details include
          row numbers starting at 2 (header row is 1).
        </p>
        <h3>Dashboard returns 400/500</h3>
        <p>
          Check the server logs (see <code>app/infrastructure/logging.py</code>) and verify the session contains
          data.
        </p>
        <h3>Frontend assets outdated</h3>
        <p>Run <code>npm run build</code>; the server rebuilds automatically when started via the helper.</p>
      </div>
    ),
  },
  {
    id: "reference-appendix",
    title: "Reference Appendix",
    content: (
      <ul className="help-list">
        <li>
          Backend configuration: <code>app/infrastructure/config.py</code>
        </li>
        <li>
          Database repositories: <code>app/infrastructure/repositories_*.py</code>
        </li>
        <li>
          Web API endpoints: <code>app/web/routes/api.py</code>
        </li>
        <li>
          Excel template: <code>app/web/static/templates/assessment_upload_template.xlsx</code>
        </li>
        <li>
          Dashboard UI: <code>frontend/src/components/DashboardPage.tsx</code>, <code>frontend/src/hooks/useDashboard.ts</code>
        </li>
        <li>
          Settings UI: <code>frontend/src/components/SettingsPage.tsx</code>
        </li>
        <li>
          Export helpers: <code>app/utils/exports.py</code>, <code>app/utils/resilience_radar.py</code>
        </li>
        <li>
          Tests: <code>tests/test_dashboard_api.py</code>, <code>tests/test_improvements.py</code>
        </li>
      </ul>
    ),
  },
];

export default function HelpPage() {
  return (
    <div className="help-page">
      <div className="help-hero card">
        <h1>Help &amp; User Guide</h1>
        <p>
          Master every feature of the resilience assessment platform from database setup to dashboards,
          exports, and bulk Excel workflows.
        </p>
        <nav className="help-toc">
          <span className="help-toc__label">Contents</span>
          <ol>
            {sections.map((section) => (
              <li key={section.id}>
                <a href={`#${section.id}`}>{section.title}</a>
              </li>
            ))}
          </ol>
        </nav>
      </div>

      {sections.map((section) => (
        <section key={section.id} id={section.id} className="help-section card">
          <h2>{section.title}</h2>
          {section.content}
        </section>
      ))}
    </div>
  );
}
