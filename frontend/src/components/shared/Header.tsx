import { ChangeEvent, useMemo } from "react";
import { Link, NavLink } from "react-router-dom";
import avatarImage from "../../assets/user-avatar.png";
import Breadcrumb from "./Breadcrumb";
import { useSessionContext } from "../../context/SessionContext";
import { useBreadcrumbContext } from "../../context/BreadcrumbContext";

function HeaderIcon() {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0d80f2] text-sm font-semibold text-white">
      R
    </div>
  );
}

export default function Header() {
  const { sessions, activeSessionId, selectSession, loading, error } = useSessionContext();
  const { items: breadcrumbItems } = useBreadcrumbContext();
  const statusText = error ? "Needs attention" : loading ? "Loading…" : "Ready";
  const statusState = error ? "status-chip--error" : loading ? "status-chip--loading" : "status-chip--ready";

  const navLinks = useMemo(
    () => [
      { label: "Dimensions", to: "/" },
      { label: "Dashboard", to: "/dashboard" },
      { label: "Settings", to: "/settings" },
      { label: "Help", to: "/help" },
    ],
    [],
  );

  const handleSessionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (!value) {
      selectSession(null);
      return;
    }
    selectSession(Number.parseInt(value, 10));
  };

  return (
    <header className="app-header">
      <div className="app-container header-bar">
        <div className="brand-block">
          <HeaderIcon />
          <div>
            <Link to="/" className="brand-title">
              Resilience Studio
            </Link>
            <div className="brand-subtitle">Operational maturity insights</div>
          </div>
        </div>

        <div className="header-nav-stack">
          <nav className="nav-links">
            {navLinks.map((link) => (
              <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
                {link.label}
              </NavLink>
            ))}
          </nav>
          {breadcrumbItems.length > 0 && (
            <div className="header-inline-breadcrumb">
              <Breadcrumb items={breadcrumbItems} />
            </div>
          )}
        </div>

        <div className="header-actions">
          <div className="session-select status-display">
            <label htmlFor="status-indicator">Status</label>
            <div id="status-indicator" className={`status-chip ${statusState}`} role="status" aria-live="polite">
              {statusText}
            </div>
          </div>
          <div className="session-select">
            <label htmlFor="session-picker">Active session</label>
            <select
              id="session-picker"
              value={activeSessionId ?? ""}
              onChange={handleSessionChange}
              disabled={loading || sessions.length === 0}
            >
              {sessions.length === 0 ? (
                <option value="">{loading ? "Loading sessions…" : "No sessions"}</option>
              ) : (
                sessions.map((session) => (
                  <option key={session.id} value={session.id}>
                    #{session.id} · {session.name}
                  </option>
                ))
              )}
            </select>
          </div>
          <div className="avatar-frame">
            <img src={avatarImage} alt="User" className="h-full w-full object-cover" />
          </div>
        </div>
      </div>

      {error && (
        <div className="app-container info-banner error" style={{ marginBottom: "0" }}>
          {error}
        </div>
      )}
    </header>
  );
}
