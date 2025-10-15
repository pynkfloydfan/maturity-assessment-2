import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { apiGet } from "../api/client";
import type { Acronym } from "../api/types";

type AcronymContextValue = {
  acronyms: Acronym[];
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
};

const AcronymContext = createContext<AcronymContextValue | undefined>(undefined);

export function AcronymProvider({ children }: { children: ReactNode }) {
  const [acronyms, setAcronyms] = useState<Acronym[]>([]);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAcronyms = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await apiGet<Acronym[]>("/api/acronyms");
      setAcronyms(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load acronyms");
      setAcronyms([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAcronyms().catch(() => {
      /* handled in fetchAcronyms */
    });
  }, [fetchAcronyms]);

  const value = useMemo<AcronymContextValue>(
    () => ({ acronyms, loading, error, refresh: fetchAcronyms }),
    [acronyms, loading, error, fetchAcronyms],
  );

  return <AcronymContext.Provider value={value}>{children}</AcronymContext.Provider>;
}

export function useAcronymContext(): AcronymContextValue {
  const context = useContext(AcronymContext);
  if (!context) {
    throw new Error("useAcronymContext must be used within an AcronymProvider");
  }
  return context;
}
