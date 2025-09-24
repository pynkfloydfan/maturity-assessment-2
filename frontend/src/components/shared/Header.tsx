import { ChangeEvent, useMemo } from "react";
import { Link, NavLink } from "react-router-dom";
import avatarImage from "../../assets/user-avatar.png";
import { useSessionContext } from "../../context/SessionContext";

function HeaderIcon() {
  return (
    <div className="flex h-8 w-8 items-center justify-center rounded-full bg-[#0d80f2] text-sm font-semibold text-white">
      R
    </div>
  );
}

export default function Header() {
  const { sessions, activeSessionId, selectSession, loading, error } = useSessionContext();

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

  const activeSession = sessions.find((session) => session.id === activeSessionId);

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

        <nav className="nav-links">
          {navLinks.map((link) => (
            <NavLink key={link.to} to={link.to} className={({ isActive }) => `nav-link${isActive ? " active" : ""}`}>
              {link.label}
            </NavLink>
          ))}
        </nav>

        <div className="header-actions">
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
          <button type="button" className="btn-secondary">
            Support
          </button>
          <div className="avatar-frame">
            <img src={avatarImage} alt="User" className="h-full w-full object-cover" />
          </div>
        </div>
      </div>

      <div className="header-sub">
        <div className="app-container header-metrics">
          <div className="metric-chip">
            <div className="metric-label">Active session</div>
            <div className="metric-value">{activeSession ? activeSession.name : "None selected"}</div>
          </div>
          <div className="metric-chip">
            <div className="metric-label">Sessions available</div>
            <div className="metric-value">{sessions.length}</div>
          </div>
          <div className="metric-chip">
            <div className="metric-label">Status</div>
            <div className="metric-value">{loading ? "Loading…" : "Ready"}</div>
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
