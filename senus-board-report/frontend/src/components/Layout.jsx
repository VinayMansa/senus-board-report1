import { NavLink } from "react-router-dom";

const NAV_ITEMS = [
  { to: "/", label: "Overview", end: true },
  { to: "/growth", label: "Growth & Revenue" },
  { to: "/profitability", label: "Profitability" },
  { to: "/cash", label: "Cash & Liquidity" },
  { to: "/solvency", label: "Solvency & Leverage" },
  { to: "/returns", label: "Returns" },
];

export default function Layout({ user, onLogout, children }) {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" />
          <span className="brand-name">Senus</span>
        </div>
        <div className="brand-sub">Board Report — FY2025</div>

        <nav className="nav">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => "nav-item" + (isActive ? " active" : "")}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <div className="user">{user?.name}</div>
          <div>{user?.email}</div>
          <button onClick={onLogout}>Sign out</button>
        </div>
      </aside>

      <main className="main">{children}</main>
    </div>
  );
}
