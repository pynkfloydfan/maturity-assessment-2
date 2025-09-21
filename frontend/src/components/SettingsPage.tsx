import { ChangeEvent, FormEvent, useEffect, useMemo, useState } from "react";
import Breadcrumb from "./shared/Breadcrumb";
import { apiGet, apiPost, apiPut } from "../api/client";
import type {
  DatabaseBackend,
  DatabaseInitRequest,
  DatabaseOperationResponse,
  DatabaseSettings,
  SeedRequest,
  SeedResponse,
  SessionListItem,
} from "../api/types";
import { useSessionContext } from "../context/SessionContext";

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

  const sortedSessions = useMemo<SessionListItem[]>(() => {
    return [...sessions].sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
  }, [sessions]);

  return (
    <div className="mx-auto flex max-w-6xl flex-col gap-8 px-6 py-10">
      <Breadcrumb items={[{ label: "Settings" }]} />
      <section className="rounded-xl border border-[#e1e6ef] bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-[#121417]">Database configuration</h2>
        <p className="mt-1 text-sm text-[#61758a]">Switch between SQLite and MySQL backends, then initialise or seed the data.</p>

        <div className="mt-4 flex flex-col gap-4">
          <div className="flex gap-6">
            <label className="flex items-center gap-2 text-sm text-[#121417]">
              <input
                type="radio"
                name="backend"
                value="sqlite"
                checked={dbForm.backend === "sqlite"}
                onChange={handleBackendChange}
              />
              SQLite
            </label>
            <label className="flex items-center gap-2 text-sm text-[#121417]">
              <input
                type="radio"
                name="backend"
                value="mysql"
                checked={dbForm.backend === "mysql"}
                onChange={handleBackendChange}
              />
              MySQL
            </label>
          </div>

          {dbForm.backend === "sqlite" && (
            <div className="flex flex-col">
              <label className="text-sm font-medium text-[#121417]" htmlFor="sqlite_path">SQLite path</label>
              <input
                id="sqlite_path"
                name="sqlite_path"
                className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                value={dbForm.sqlite_path}
                onChange={handleChange}
              />
            </div>
          )}

          {dbForm.backend === "mysql" && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#121417]" htmlFor="mysql_host">Host</label>
                <input
                  id="mysql_host"
                  name="mysql_host"
                  className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                  value={dbForm.mysql_host}
                  onChange={handleChange}
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#121417]" htmlFor="mysql_port">Port</label>
                <input
                  id="mysql_port"
                  name="mysql_port"
                  className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                  value={dbForm.mysql_port}
                  onChange={handleChange}
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#121417]" htmlFor="mysql_user">User</label>
                <input
                  id="mysql_user"
                  name="mysql_user"
                  className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                  value={dbForm.mysql_user}
                  onChange={handleChange}
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#121417]" htmlFor="mysql_password">Password</label>
                <input
                  id="mysql_password"
                  name="mysql_password"
                  type="password"
                  className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                  value={dbForm.mysql_password}
                  onChange={handleChange}
                />
              </div>
              <div className="flex flex-col">
                <label className="text-sm font-medium text-[#121417]" htmlFor="mysql_database">Database</label>
                <input
                  id="mysql_database"
                  name="mysql_database"
                  className="mt-1 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
                  value={dbForm.mysql_database}
                  onChange={handleChange}
                />
              </div>
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <button
              type="button"
              className="rounded-md bg-[#0d80f2] px-4 py-2 text-sm font-medium text-white shadow"
              onClick={handleSaveConfig}
            >
              Save configuration
            </button>
            <button
              type="button"
              className="rounded-md border border-[#d0d7e3] px-4 py-2 text-sm font-medium text-[#121417]"
              onClick={handleInit}
            >
              Initialise tables
            </button>
          </div>

          {dbFeedback && (
            <p className={`text-sm ${dbFeedback.type === "success" ? "text-green-600" : "text-red-600"}`}>
              {dbFeedback.message}
            </p>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-[#e1e6ef] bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-[#121417]">Seed dataset</h2>
        <p className="mt-1 text-sm text-[#61758a]">Populate dimensions, themes, and guidance from the enhanced spreadsheet.</p>
        <div className="mt-4 flex flex-col gap-3">
          <label className="text-sm font-medium text-[#121417]" htmlFor="excel_path">Spreadsheet path</label>
          <input
            id="excel_path"
            className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
            value={excelPath}
            onChange={(event) => setExcelPath(event.target.value)}
          />
          <div className="flex gap-3">
            <button
              type="button"
              className="rounded-md bg-[#0d80f2] px-4 py-2 text-sm font-medium text-white shadow"
              onClick={handleSeed}
            >
              Seed from Excel
            </button>
            <button
              type="button"
              className="rounded-md border border-[#d0d7e3] px-4 py-2 text-sm font-medium text-[#121417]"
              onClick={refreshSessions}
            >
              Refresh sessions
            </button>
          </div>
          {seedFeedback && (
            <p className={`text-sm ${seedFeedback.type === "success" ? "text-green-600" : "text-red-600"}`}>
              {seedFeedback.message}
            </p>
          )}
          {seedDetails && (
            <pre className="max-h-60 overflow-auto rounded-md bg-[#f5f7fb] p-3 text-xs text-[#121417]">{seedDetails}</pre>
          )}
        </div>
      </section>

      <section className="rounded-xl border border-[#e1e6ef] bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-[#121417]">Sessions</h2>
        <p className="mt-1 text-sm text-[#61758a]">Create new sessions or combine existing ones into a master.</p>
        <div className="mt-4 grid gap-6 md:grid-cols-2">
          <form className="flex flex-col gap-3" onSubmit={handleCreateSession}>
            <h3 className="text-lg font-medium text-[#121417]">Create session</h3>
            <input
              className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
              placeholder="Session name"
              value={newSession.name}
              onChange={(event) => setNewSession((prev) => ({ ...prev, name: event.target.value }))}
            />
            <input
              className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
              placeholder="Assessor (optional)"
              value={newSession.assessor}
              onChange={(event) => setNewSession((prev) => ({ ...prev, assessor: event.target.value }))}
            />
            <input
              className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
              placeholder="Organization (optional)"
              value={newSession.organization}
              onChange={(event) => setNewSession((prev) => ({ ...prev, organization: event.target.value }))}
            />
            <input
              className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
              placeholder="Notes (optional)"
              value={newSession.notes}
              onChange={(event) => setNewSession((prev) => ({ ...prev, notes: event.target.value }))}
            />
            <button
              type="submit"
              className="self-start rounded-md bg-[#0d80f2] px-4 py-2 text-sm font-medium text-white shadow"
            >
              Create session
            </button>
          </form>

          <div className="flex flex-col gap-3">
            <h3 className="text-lg font-medium text-[#121417]">Combine sessions</h3>
            <label className="text-sm text-[#61758a]" htmlFor="combine_select">
              Hold Ctrl/Cmd to select multiple sessions
            </label>
            <select
              id="combine_select"
              className="h-40 rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
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
              className="rounded-md border border-[#d0d7e3] px-3 py-2 text-sm"
              value={combineName}
              onChange={(event) => setCombineName(event.target.value)}
              placeholder="Master session name"
            />
            <button
              type="button"
              className="self-start rounded-md border border-[#d0d7e3] px-4 py-2 text-sm font-medium text-[#121417]"
              onClick={handleCombineSessions}
            >
              Combine selected
            </button>
          </div>
        </div>
        {sessionFeedback && (
          <p className={`mt-2 text-sm ${sessionFeedback.type === "success" ? "text-green-600" : "text-red-600"}`}>
            {sessionFeedback.message}
          </p>
        )}
      </section>
    </div>
  );
}
