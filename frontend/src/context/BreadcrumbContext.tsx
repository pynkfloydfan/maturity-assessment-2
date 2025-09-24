import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";

export interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbContextValue {
  items: BreadcrumbItem[];
  setItems: (items: BreadcrumbItem[]) => void;
}

const BreadcrumbContext = createContext<BreadcrumbContextValue | undefined>(undefined);

export function BreadcrumbProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<BreadcrumbItem[]>([]);

  const value = useMemo(() => ({ items, setItems }), [items]);

  return <BreadcrumbContext.Provider value={value}>{children}</BreadcrumbContext.Provider>;
}

export function useBreadcrumbContext() {
  const context = useContext(BreadcrumbContext);
  if (!context) {
    throw new Error("useBreadcrumbContext must be used within a BreadcrumbProvider");
  }
  return context;
}

export function usePageBreadcrumb(items: BreadcrumbItem[] | null | undefined) {
  const { setItems } = useBreadcrumbContext();
  const trail = useMemo(() => items ?? [], [items]);

  useEffect(() => {
    setItems(trail);
    return () => setItems([]);
  }, [setItems, trail]);
}
