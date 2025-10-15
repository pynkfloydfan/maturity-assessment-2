import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export type NavigationAttemptType = "link" | "popstate";

export interface NavigationAttempt {
  type: NavigationAttemptType;
  to: string | null;
}

export interface NavigationBlocker {
  pending: NavigationAttempt | null;
  proceed: () => void;
  reset: () => void;
}

function isModifiedEvent(event: MouseEvent) {
  return event.metaKey || event.altKey || event.ctrlKey || event.shiftKey;
}

export function useNavigationBlocker(shouldBlock: boolean): NavigationBlocker {
  const navigate = useNavigate();
  const location = useLocation();
  const shouldBlockRef = useRef(shouldBlock);
  const [pending, setPending] = useState<NavigationAttempt | null>(null);
  const pendingRef = useRef<NavigationAttempt | null>(null);
  const currentPathRef = useRef(`${location.pathname}${location.search}${location.hash}`);

  useEffect(() => {
    shouldBlockRef.current = shouldBlock;
    if (!shouldBlock) {
      pendingRef.current = null;
      setPending(null);
    }
  }, [shouldBlock]);

  useEffect(() => {
    currentPathRef.current = `${location.pathname}${location.search}${location.hash}`;
  }, [location]);

  const setPendingAttempt = useCallback((attempt: NavigationAttempt) => {
    pendingRef.current = attempt;
    setPending(attempt);
  }, []);

  useEffect(() => {
    const handleLinkClick = (event: MouseEvent) => {
      if (!shouldBlockRef.current || pendingRef.current) {
        return;
      }
      if (event.defaultPrevented || event.button !== 0 || isModifiedEvent(event)) {
        return;
      }
      const target = event.target as HTMLElement | null;
      if (!target) return;
      const anchor = target.closest("a[href]");
      if (!anchor) return;
      const href = anchor.getAttribute("href");
      if (!href || href.startsWith("javascript:")) return;
      if (anchor.target && anchor.target !== "") return;
      const url = new URL(href, window.location.href);
      if (url.origin !== window.location.origin) return;
      const destination = `${url.pathname}${url.search}${url.hash}`;
      if (destination === currentPathRef.current) return;
      event.preventDefault();
      setPendingAttempt({ type: "link", to: destination });
    };

    document.addEventListener("click", handleLinkClick, true);
    return () => {
      document.removeEventListener("click", handleLinkClick, true);
    };
  }, [setPendingAttempt]);

  useEffect(() => {
    const handlePopState = () => {
      if (!shouldBlockRef.current || pendingRef.current) {
        return;
      }
      const destination = `${window.location.pathname}${window.location.search}${window.location.hash}`;
      const currentPath = currentPathRef.current;
      if (destination === currentPath) {
        return;
      }
      setPendingAttempt({ type: "popstate", to: destination });
      navigate(currentPath, { replace: true });
    };

    window.addEventListener("popstate", handlePopState);
    return () => {
      window.removeEventListener("popstate", handlePopState);
    };
  }, [navigate, setPendingAttempt]);

  const proceed = useCallback(() => {
    const attempt = pendingRef.current;
    if (!attempt) {
      return;
    }
    pendingRef.current = null;
    setPending(null);
    if (attempt.to) {
      navigate(attempt.to, { replace: attempt.type === "popstate" });
    }
  }, [navigate]);

  const reset = useCallback(() => {
    pendingRef.current = null;
    setPending(null);
  }, []);

  return useMemo(
    () => ({
      pending,
      proceed,
      reset,
    }),
    [pending, proceed, reset],
  );
}
