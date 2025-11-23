import { ChangeEvent, FocusEvent, useMemo, useState } from "react";
import { Link, NavLink } from "react-router-dom";
import avatarImage from "../../assets/user-avatar.png";
import Breadcrumb from "./Breadcrumb";
import { useSessionContext } from "../../context/SessionContext";
import { useBreadcrumbContext } from "../../context/BreadcrumbContext";
import { useDimensions } from "../../hooks/useDimensions";

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
  const { dimensions, loading: dimensionsLoading } = useDimensions();
  const [dimensionMenuOpen, setDimensionMenuOpen] = useState(false);
  const statusText = error ? "Needs attention" : loading ? "Loading…" : "Ready";
  const statusState = error ? "status-chip--error" : loading ? "status-chip--loading" : "status-chip--ready";

  const navLinks = useMemo(
    () => [
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
            <div
              className={`nav-dropdown-wrapper${dimensionMenuOpen ? " nav-dropdown-wrapper--open" : ""}`}
              onMouseEnter={() => setDimensionMenuOpen(true)}
              onMouseLeave={() => setDimensionMenuOpen(false)}
              onFocus={() => setDimensionMenuOpen(true)}
              onBlur={(event: FocusEvent<HTMLDivElement>) => {
                if (!event.currentTarget.contains(event.relatedTarget)) {
                  setDimensionMenuOpen(false);
                }
              }}
            >
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `nav-link nav-link--dropdown${isActive ? " active" : ""}`
                }
                aria-haspopup="true"
                aria-expanded={dimensionMenuOpen}
                title="Hover to jump to a dimension"
              >
                Dimensions
                <span className="nav-link__caret" aria-hidden="true">▾</span>
              </NavLink>
              <div className="nav-dropdown" role="menu" aria-label="All dimensions">
                {dimensionsLoading && <div className="nav-dropdown__item muted">Loading dimensions…</div>}
                {!dimensionsLoading && dimensions.length === 0 && (
                  <div className="nav-dropdown__item muted">No dimensions available</div>
                )}
                {dimensions.map((dimension) => (
                  <Link
                    key={dimension.id}
                    to={`/dimensions/${dimension.id}/assessment`}
                    className="nav-dropdown__item"
                    role="menuitem"
                    onClick={() => setDimensionMenuOpen(false)}
                  >
                    {dimension.name}
                  </Link>
                ))}
              </div>
            </div>
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
