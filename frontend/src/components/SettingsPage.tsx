import { ChangeEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { apiGet, apiPost, apiPut, apiUpload } from "../api/client";
import type {
  DatabaseBackend,
  DatabaseInitRequest,
  DatabaseOperationResponse,
  DatabaseSettings,
  SeedRequest,
  SeedResponse,
  ImportResponse,
  SessionListItem,
} from "../api/types";
import { useSessionContext } from "../context/SessionContext";
import { usePageBreadcrumb } from "../context/BreadcrumbContext";

const DEFAULT_SQLITE_PATH = "./resilience.db";
const DEFAULT_EXCEL_PATH = "app/source_data/enhanced_operational_resilience_maturity_v6.xlsx";

type Feedback = { type: "success" | "error"; message: string } | null;

interface DatabaseFormState {
  backend: DatabaseBackend;
  sqlite_path: string;
  mysql_host: string;
  mysql_port: string;
  mysql_user: string;
  mysql_password: string;
  mysql_database: string;
}

const INITIAL_DB_FORM: DatabaseFormState = {
  backend: "sqlite",
  sqlite_path: DEFAULT_SQLITE_PATH,
  mysql_host: "localhost",
  mysql_port: "3306",
  mysql_user: "root",
  mysql_password: "",
  mysql_database: "resilience",
};

function toInitRequest(state: DatabaseFormState, includePassword = false): DatabaseInitRequest {
  const payload: DatabaseInitRequest = {
    backend: state.backend,
  };

  if (state.backend === "sqlite") {
    payload.sqlite_path = state.sqlite_path || DEFAULT_SQLITE_PATH;
  } else {
    payload.sqlite_path = state.sqlite_path || DEFAULT_SQLITE_PATH;
    payload.mysql_host = state.mysql_host || null;
    payload.mysql_port = state.mysql_port ? Number.parseInt(state.mysql_port, 10) : null;
    payload.mysql_user = state.mysql_user || null;
    payload.mysql_database = state.mysql_database || null;
    if (includePassword) {
      payload.mysql_password = state.mysql_password || null;
    }
  }

  return payload;
}

function mergeSettingsIntoForm(form: DatabaseFormState, settings: DatabaseSettings | null): DatabaseFormState {
  if (!settings) {
    return form;
  }
  return {
    backend: settings.backend ?? form.backend,
    sqlite_path: settings.sqlite_path ?? form.sqlite_path,
    mysql_host: settings.mysql_host ?? form.mysql_host,
    mysql_port: settings.mysql_port != null ? String(settings.mysql_port) : form.mysql_port,
    mysql_user: settings.mysql_user ?? form.mysql_user,
    mysql_password: form.mysql_password,
    mysql_database: settings.mysql_database ?? form.mysql_database,
  };
}

export default function SettingsPage() {
  const { sessions, refreshSessions } = useSessionContext();
  usePageBreadcrumb(null);
  const [dbForm, setDbForm] = useState<DatabaseFormState>(INITIAL_DB_FORM);
  const [excelPath, setExcelPath] = useState<string>(DEFAULT_EXCEL_PATH);
  const [dbFeedback, setDbFeedback] = useState<Feedback>(null);
  const [seedFeedback, setSeedFeedback] = useState<Feedback>(null);
  const [seedDetails, setSeedDetails] = useState<string | null>(null);
  const [sessionFeedback, setSessionFeedback] = useState<Feedback>(null);
  const [combineSelection, setCombineSelection] = useState<string[]>([]);
  const [combineName, setCombineName] = useState<string>("Combined Assessment");
  const [newSession, setNewSession] = useState({
    name: "Baseline Assessment",
    assessor: "",
    organization: "",
    notes: "",
  });
  const [uploadFeedback, setUploadFeedback] = useState<Feedback>(null);
  const [uploadErrors, setUploadErrors] = useState<string[] | null>(null);
  const [uploadSessionId, setUploadSessionId] = useState<string>("");
  const [hasUploadFile, setHasUploadFile] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    apiGet<DatabaseSettings>("/api/settings/database")
      .then((settings) => {
        setDbForm((prev) => mergeSettingsIntoForm(prev, settings));
        if (settings.backend === "sqlite" && settings.sqlite_path) {
          setExcelPath((prev) => prev || DEFAULT_EXCEL_PATH);
        }
      })
      .catch(() => {
        setDbFeedback({ type: "error", message: "Failed to load database settings" });
      });
  }, []);

  useEffect(() => {
    if (sessions.length && !uploadSessionId) {
      setUploadSessionId(String(sessions[0].id));
    }
  }, [sessions, uploadSessionId]);

  const handleBackendChange = (event: ChangeEvent<HTMLInputElement>) => {
    const backend = event.target.value as DatabaseBackend;
    setDbForm((prev) => ({ ...prev, backend }));
  };

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, value } = event.target;
    setDbForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSaveConfig = async () => {
    try {
      const response = await apiPut<DatabaseSettings>("/api/settings/database", toInitRequest(dbForm, true));
      setDbForm((prev) => mergeSettingsIntoForm(prev, response));
      setDbFeedback({ type: "success", message: "Database settings saved" });
    } catch (err) {
      setDbFeedback({ type: "error", message: err instanceof Error ? err.message : "Failed to save settings" });
    }
  };

  const runOperation = async (
    endpoint: string,
    includePassword = false,
    extraPayload: Partial<SeedRequest> = {},
  ) => {
    const payload: SeedRequest = {
      ...toInitRequest(dbForm, includePassword),
      ...extraPayload,
    };
    return apiPost<DatabaseOperationResponse | SeedResponse>(endpoint, payload);
  };

  const handleInit = async () => {
    try {
      const result = await runOperation("/api/settings/database/init", true);
      setDbFeedback({ type: result.status, message: result.message });
    } catch (err) {
      setDbFeedback({ type: "error", message: err instanceof Error ? err.message : "Failed to initialise" });
    }
  };

  const handleSeed = async () => {
    try {
      const result = (await runOperation("/api/settings/database/seed", true, { excel_path: excelPath })) as SeedResponse;
      setSeedFeedback({ type: result.status, message: result.message });
      if (result.status === "ok") {
        setSeedDetails(result.stdout || null);
        refreshSessions();
      } else {
        setSeedDetails(result.stderr || result.stdout || null);
      }
    } catch (err) {
      setSeedFeedback({ type: "error", message: err instanceof Error ? err.message : "Failed to seed database" });
    }
  };

  const handleCreateSession = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    if (!newSession.name.trim()) {
      setSessionFeedback({ type: "error", message: "Session name is required" });
      return;
    }
    try {
      await apiPost("/api/sessions", {
        name: newSession.name.trim(),
        assessor: newSession.assessor.trim() || null,
        organization: newSession.organization.trim() || null,
        notes: newSession.notes.trim() || null,
      });
      setSessionFeedback({ type: "success", message: "Session created" });
      refreshSessions();
    } catch (err) {
      setSessionFeedback({ type: "error", message: err instanceof Error ? err.message : "Failed to create session" });
    }
  };

  const handleCombineSessions = async () => {
    const ids = combineSelection.map((value) => Number.parseInt(value, 10)).filter((id) => !Number.isNaN(id));
    if (ids.length === 0) {
      setSessionFeedback({ type: "error", message: "Select at least one source session" });
      return;
    }
    try {
      await apiPost("/api/sessions/combine", {
        source_session_ids: ids,
        name: combineName.trim() || "Combined Session",
      });
      setSessionFeedback({ type: "success", message: "Master session created" });
      refreshSessions();
    } catch (err) {
      setSessionFeedback({ type: "error", message: err instanceof Error ? err.message : "Failed to combine sessions" });
    }
  };

  const handleUploadFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] ?? null;
    setHasUploadFile(Boolean(file));
    setUploadFeedback(null);
    setUploadErrors(null);
  };

  const handleUploadAssessment = async () => {
    if (!uploadSessionId) {
      setUploadFeedback({ type: "error", message: "Select a target session" });
      return;
    }

    const file = fileInputRef.current?.files?.[0] ?? null;
    if (!file) {
      setUploadFeedback({ type: "error", message: "Choose an Excel file to upload" });
      return;
    }

    const formData = new FormData();
    formData.append("file", file);

    setUploadFeedback(null);
    setUploadErrors(null);

    try {
      const result = await apiUpload<ImportResponse>(
        `/api/sessions/${uploadSessionId}/imports/xlsx`,
        formData,
      );

      if (result.status === "ok") {
        setUploadFeedback({ type: "success", message: result.message });
        setUploadErrors(null);
        setHasUploadFile(false);
        if (fileInputRef.current) {
          fileInputRef.current.value = "";
        }
        refreshSessions();
      } else {
        setUploadFeedback({ type: "error", message: result.message });
        const errors = result.errors?.map((error) => {
          const field = typeof error.field === "string" ? error.field : "Row";
          const details =
            error.details && typeof error.details === "object"
              ? JSON.stringify(error.details)
              : undefined;
          return details ? `${field}: ${error.message} (${details})` : `${field}: ${error.message}`;
        });
        setUploadErrors(errors && errors.length ? errors : null);
      }
    } catch (err) {
      setUploadFeedback({
        type: "error",
        message: err instanceof Error ? err.message : "Failed to import assessment",
      });
      setUploadErrors(null);
    }
  };

  const sortedSessions = useMemo<SessionListItem[]>(() => {
    return [...sessions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [sessions]);

  return (
    <div className="page-section">
      <div className="page-hero">
        <div className="pill">Workspace Controls</div>
        <div>
          <h1>Configure your resilience studio</h1>
          <p>
            Manage database connectivity, seed the enhanced dataset, and orchestrate assessment
            sessions without leaving the Settings hub.
          </p>
        </div>
        <div className="status-card">
          <div className="status-item">
            <div className="status-label">Database backend</div>
            <div className="status-value">{dbForm.backend === "mysql" ? "MySQL" : "SQLite"}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Sessions available</div>
            <div className="status-value">{sessions.length}</div>
          </div>
          <div className="status-item">
            <div className="status-label">Spreadsheet source</div>
            <div className="status-value">{excelPath ? "Configured" : "Not set"}</div>
          </div>
        </div>
      </div>

      <div className="settings-grid">
        <div className="settings-column">
          <section className="settings-card">
            <div className="settings-card-header">
              <h2 className="settings-card-title">Database configuration</h2>
              <p className="settings-card-subtitle">
                Switch between SQLite and MySQL backends, then initialise the schema when you’re ready.
              </p>
            </div>

            <div className="radio-row" role="radiogroup" aria-label="Database backend">
              <label className="radio-pill" htmlFor="backend-sqlite">
                <input
                  id="backend-sqlite"
                  type="radio"
                  name="backend"
                  value="sqlite"
                  checked={dbForm.backend === "sqlite"}
                  onChange={handleBackendChange}
                />
                <span>SQLite</span>
              </label>
              <label className="radio-pill" htmlFor="backend-mysql">
                <input
                  id="backend-mysql"
                  type="radio"
                  name="backend"
                  value="mysql"
                  checked={dbForm.backend === "mysql"}
                  onChange={handleBackendChange}
                />
                <span>MySQL</span>
              </label>
            </div>

            {dbForm.backend === "sqlite" && (
              <div className="form-grid">
                <label className="field-group" htmlFor="sqlite_path">
                  <span className="field-label">SQLite path</span>
                  <input
                    id="sqlite_path"
                    name="sqlite_path"
                    className="input-control"
                    value={dbForm.sqlite_path}
                    onChange={handleChange}
                  />
                </label>
              </div>
            )}

            {dbForm.backend === "mysql" && (
              <div className="form-grid two-column">
                <label className="field-group" htmlFor="mysql_host">
                  <span className="field-label">Host</span>
                  <input
                    id="mysql_host"
                    name="mysql_host"
                    className="input-control"
                    value={dbForm.mysql_host}
                    onChange={handleChange}
                  />
                </label>
                <label className="field-group" htmlFor="mysql_port">
                  <span className="field-label">Port</span>
                  <input
                    id="mysql_port"
                    name="mysql_port"
                    className="input-control"
                    value={dbForm.mysql_port}
                    onChange={handleChange}
                  />
                </label>
                <label className="field-group" htmlFor="mysql_user">
                  <span className="field-label">User</span>
                  <input
                    id="mysql_user"
                    name="mysql_user"
                    className="input-control"
                    value={dbForm.mysql_user}
                    onChange={handleChange}
                  />
                </label>
                <label className="field-group" htmlFor="mysql_password">
                  <span className="field-label">Password</span>
                  <input
                    id="mysql_password"
                    name="mysql_password"
                    type="password"
                    className="input-control"
                    value={dbForm.mysql_password}
                    onChange={handleChange}
                  />
                </label>
                <label className="field-group" htmlFor="mysql_database">
                  <span className="field-label">Database</span>
                  <input
                    id="mysql_database"
                    name="mysql_database"
                    className="input-control"
                    value={dbForm.mysql_database}
                    onChange={handleChange}
                  />
                </label>
              </div>
            )}

            <div className="settings-card-actions">
              <button type="button" className="btn-primary" onClick={handleSaveConfig}>
                Save configuration
              </button>
              <button type="button" className="btn-secondary" onClick={handleInit}>
                Initialise tables
              </button>
            </div>

            {dbFeedback && (
              <p className={`feedback-inline ${dbFeedback.type}`}>{dbFeedback.message}</p>
            )}
          </section>

          <section className="settings-card">
            <div className="settings-card-header">
              <h2 className="settings-card-title">Seed dataset</h2>
              <p className="settings-card-subtitle">
                Populate dimensions, themes, and guidance from the enhanced spreadsheet.
              </p>
            </div>

            <label className="field-group" htmlFor="excel_path">
              <span className="field-label">Spreadsheet path</span>
              <input
                id="excel_path"
                className="input-control"
                value={excelPath}
                onChange={(event) => setExcelPath(event.target.value)}
              />
              <span className="field-hint">Defaults to the enhanced operational resilience workbook.</span>
            </label>

            <div className="settings-card-actions">
              <button type="button" className="btn-primary" onClick={handleSeed}>
                Seed from Excel
              </button>
              <button type="button" className="btn-secondary" onClick={refreshSessions}>
                Refresh sessions
              </button>
            </div>

          {seedFeedback && (
            <p className={`feedback-inline ${seedFeedback.type}`}>{seedFeedback.message}</p>
          )}

          {seedDetails && <pre className="seed-log">{seedDetails}</pre>}
        </section>

        <section className="settings-card">
          <div className="settings-card-header">
            <h2 className="settings-card-title">Upload assessment</h2>
            <p className="settings-card-subtitle">
              Import ratings and comments from an Excel export into an existing session.
            </p>
          </div>

          {sessions.length ? (
            <>
              <label className="field-group" htmlFor="upload_session">
                <span className="field-label">Target session</span>
                <select
                  id="upload_session"
                  className="input-control"
                  value={uploadSessionId}
                  onChange={(event) => setUploadSessionId(event.target.value)}
                >
                  {sortedSessions.map((session) => (
                    <option key={session.id} value={String(session.id)}>
                      #{session.id} · {session.name}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field-group" htmlFor="upload_file">
                <span className="field-label">Assessment workbook</span>
                <input
                  id="upload_file"
                  ref={fileInputRef}
                  className="input-control"
                  type="file"
                  accept=".xlsx,.xls"
                  onChange={handleUploadFileChange}
                />
                <span className="field-hint">
                  Start from the{' '}
                  <a href="/static/templates/assessment_upload_template.xlsx" download>
                    assessment upload template
                  </a>{' '}
                  to ensure the column layout matches expectations.
                </span>
              </label>

              <div className="settings-card-actions">
                <button
                  type="button"
                  className="btn-primary"
                  onClick={handleUploadAssessment}
                  disabled={!hasUploadFile}
                >
                  Upload assessment
                </button>
              </div>
            </>
          ) : (
            <p className="field-hint">Create a session first to enable uploads.</p>
          )}

          {uploadFeedback && (
            <p className={`feedback-inline ${uploadFeedback.type}`}>{uploadFeedback.message}</p>
          )}

          {uploadErrors && (
            <ul className="upload-error-list">
              {uploadErrors.map((line, index) => (
                <li key={index}>{line}</li>
              ))}
            </ul>
          )}
        </section>
      </div>

        <div className="settings-column">
          <section className="settings-card">
            <div className="settings-card-header">
              <h2 className="settings-card-title">Sessions</h2>
              <p className="settings-card-subtitle">
                Create new assessment sessions or blend existing ones into a combined master.
              </p>
            </div>

            <div className="form-grid two-column">
              <form className="field-group" onSubmit={handleCreateSession}>
                <span className="field-label">Create session</span>
                <input
                  className="input-control"
                  placeholder="Session name"
                  value={newSession.name}
                  onChange={(event) => setNewSession((prev) => ({ ...prev, name: event.target.value }))}
                />
                <input
                  className="input-control"
                  placeholder="Assessor (optional)"
                  value={newSession.assessor}
                  onChange={(event) => setNewSession((prev) => ({ ...prev, assessor: event.target.value }))}
                />
                <input
                  className="input-control"
                  placeholder="Organization (optional)"
                  value={newSession.organization}
                  onChange={(event) => setNewSession((prev) => ({ ...prev, organization: event.target.value }))}
                />
                <input
                  className="input-control"
                  placeholder="Notes (optional)"
                  value={newSession.notes}
                  onChange={(event) => setNewSession((prev) => ({ ...prev, notes: event.target.value }))}
                />
                <button type="submit" className="btn-primary">
                  Create session
                </button>
              </form>

              <div className="field-group">
                <span className="field-label">Combine sessions</span>
                <span className="field-hint">Hold Ctrl/Cmd to choose multiple source sessions.</span>
                <select
                  id="combine_select"
                  className="input-control session-multi"
                  multiple
                  value={combineSelection}
                  onChange={(event) => {
                    const values = Array.from(event.target.selectedOptions).map((option) => option.value);
                    setCombineSelection(values);
                  }}
                >
                  {sortedSessions.map((session) => (
                    <option key={session.id} value={String(session.id)}>
                      #{session.id} · {session.name}
                    </option>
                  ))}
                </select>
                <input
                  className="input-control"
                  value={combineName}
                  onChange={(event) => setCombineName(event.target.value)}
                  placeholder="Master session name"
                />
                <button type="button" className="btn-secondary" onClick={handleCombineSessions}>
                  Combine selected
                </button>
              </div>
            </div>

            {sessionFeedback && (
              <p className={`feedback-inline ${sessionFeedback.type}`}>{sessionFeedback.message}</p>
            )}
          </section>

          <section className="settings-card">
            <div className="settings-card-header">
              <h2 className="settings-card-title">Coming soon</h2>
              <p className="settings-card-subtitle">
                Planned controls that build on the refreshed design language for the Settings hub.
              </p>
            </div>

            <div className="feature-list">
              <div className="feature-item">
                <span className="feature-icon">D</span>
                <div className="feature-copy">
                  <span className="feature-title">Data export history</span>
                  <span className="feature-description">
                    Access downloadable archives of previous exports with timestamps and owners.
                  </span>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">T</span>
                <div className="feature-copy">
                  <span className="feature-title">Brand &amp; theming controls</span>
                  <span className="feature-description">
                    Upload custom logos, adjust the colour tokens, and preview changes instantly.
                  </span>
                </div>
              </div>
              <div className="feature-item">
                <span className="feature-icon">S</span>
                <div className="feature-copy">
                  <span className="feature-title">System health</span>
                  <span className="feature-description">
                    Highlight the latest migration, pending actions, and actionable resilience alerts.
                  </span>
                </div>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
