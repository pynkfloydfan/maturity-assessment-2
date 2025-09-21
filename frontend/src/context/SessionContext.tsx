import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { apiGet } from "../api/client";
import type { SessionDetail, SessionListItem, SessionSummary } from "../api/types";

interface SessionContextValue {
  sessions: SessionListItem[];
  activeSessionId: number | null;
  activeSessionSummary: SessionSummary | null;
  loading: boolean;
  error: string | null;
  refreshSessions: () => Promise<void>;
  selectSession: (sessionId: number | null) => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

const STORAGE_KEY = "resilience.activeSessionId";

async function fetchSessions(): Promise<SessionListItem[]> {
  return apiGet<SessionListItem[]>("/api/sessions");
}

async function fetchSessionSummary(sessionId: number): Promise<SessionDetail> {
  return apiGet<SessionDetail>(`/api/sessions/${sessionId}`);
}

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [sessions, setSessions] = useState<SessionListItem[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<number | null>(null);
  const [activeSessionSummary, setActiveSessionSummary] = useState<SessionSummary | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const loadActiveSessionFromStorage = useCallback(() => {
    if (typeof window === "undefined") return null;
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (!stored) return null;
    const parsed = Number.parseInt(stored, 10);
    return Number.isFinite(parsed) ? parsed : null;
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchSessions();
      setSessions(data);

      if (data.length === 0) {
        setActiveSessionId(null);
        setActiveSessionSummary(null);
        if (typeof window !== "undefined") {
          window.localStorage.removeItem(STORAGE_KEY);
        }
        return;
      }

      const storedId = loadActiveSessionFromStorage();
      const initialSession = data.find((session) => session.id === storedId) ?? data[0];
      setActiveSessionId(initialSession.id);
      if (typeof window !== "undefined") {
        window.localStorage.setItem(STORAGE_KEY, String(initialSession.id));
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sessions");
    } finally {
      setLoading(false);
    }
  }, [loadActiveSessionFromStorage]);

  useEffect(() => {
    refreshSessions();
  }, [refreshSessions]);

  useEffect(() => {
    if (!activeSessionId) {
      setActiveSessionSummary(null);
      return;
    }

    let isMounted = true;

    fetchSessionSummary(activeSessionId)
      .then((detail) => {
        if (!isMounted) return;
        setActiveSessionSummary(detail.summary);
        if (typeof window !== "undefined") {
          window.localStorage.setItem(STORAGE_KEY, String(detail.summary.id));
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        setError(err instanceof Error ? err.message : "Failed to load session details");
        setActiveSessionSummary(null);
      });

    return () => {
      isMounted = false;
    };
  }, [activeSessionId]);

  const selectSession = useCallback((sessionId: number | null) => {
    setActiveSessionId(sessionId);
    if (typeof window !== "undefined") {
      if (sessionId === null) {
        window.localStorage.removeItem(STORAGE_KEY);
      } else {
        window.localStorage.setItem(STORAGE_KEY, String(sessionId));
      }
    }
  }, []);

  const value = useMemo<SessionContextValue>(() => ({
    sessions,
    activeSessionId,
    activeSessionSummary,
    loading,
    error,
    refreshSessions,
    selectSession,
  }), [sessions, activeSessionId, activeSessionSummary, loading, error, refreshSessions, selectSession]);

  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSessionContext(): SessionContextValue {
  const ctx = useContext(SessionContext);
  if (!ctx) {
    throw new Error("useSessionContext must be used within a SessionProvider");
  }
  return ctx;
}
