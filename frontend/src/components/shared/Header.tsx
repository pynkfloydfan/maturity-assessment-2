import { ChangeEvent } from "react";
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

  const handleSessionChange = (event: ChangeEvent<HTMLSelectElement>) => {
    const value = event.target.value;
    if (!value) {
      selectSession(null);
      return;
    }
    selectSession(Number.parseInt(value, 10));
  };

  return (
    <div className="w-full border-b border-[#e5e8eb] bg-white">
      <div className="flex flex-wrap items-center justify-between gap-4 px-10 py-3">
        <div className="flex items-center gap-4">
          <HeaderIcon />
          <Link to="/" className="text-lg font-bold text-[#121417] no-underline">
            Resilience Platform
          </Link>
        </div>
        <div className="flex flex-wrap items-center gap-8">
          <nav className="flex items-center gap-9 text-sm">
            <NavLink to="/" className={({ isActive }) => (isActive ? "text-[#121417] font-medium" : "text-[#61758a] font-medium")}>Dimensions</NavLink>
            <NavLink to="/assessments" className={({ isActive }) => (isActive ? "text-[#121417] font-medium" : "text-[#61758a] font-medium")}>Assessments</NavLink>
            <NavLink to="/dashboard" className={({ isActive }) => (isActive ? "text-[#121417] font-medium" : "text-[#61758a] font-medium")}>Dashboard</NavLink>
            <NavLink to="/settings" className={({ isActive }) => (isActive ? "text-[#121417] font-medium" : "text-[#61758a] font-medium")}>Settings</NavLink>
            <NavLink to="/help" className={({ isActive }) => (isActive ? "text-[#121417] font-medium" : "text-[#61758a] font-medium")}>Help</NavLink>
          </nav>
          <div className="flex items-center gap-3">
            <label className="text-xs uppercase tracking-wide text-[#61758a]" htmlFor="session-picker">
              Active Session
            </label>
            <select
              id="session-picker"
              className="min-w-[220px] rounded-md border border-[#d0d7e3] bg-white px-3 py-1.5 text-sm focus:border-[#0d80f2] focus:outline-none"
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
            {error && <span className="text-xs text-red-600">{error}</span>}
          </div>
          <div
            className="h-10 w-10 overflow-hidden rounded-full border border-[#e1e6ef]"
          >
            <img src={avatarImage} alt="User" className="h-full w-full object-cover" />
          </div>
        </div>
      </div>
    </div>
  );
}
