import { BarChart3, Database, FileSearch, Files, PanelLeftClose, PanelLeftOpen, RefreshCw } from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
import { Button } from "../ui/Button";

export type PageKey = "dashboard" | "sessions" | "search";

const navItems: Array<{ key: PageKey; label: string; icon: ReactNode }> = [
  { key: "dashboard", label: "Dashboard", icon: <BarChart3 size={18} /> },
  { key: "sessions", label: "Sessions", icon: <Files size={18} /> },
  { key: "search", label: "Recruiter Search", icon: <FileSearch size={18} /> },
];

export function AppLayout({
  page,
  onPageChange,
  children,
  onRefresh,
  busy,
}: {
  page: PageKey;
  onPageChange: (page: PageKey) => void;
  children: ReactNode;
  onRefresh: () => void;
  busy?: boolean;
}) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <main className={`app-shell ${collapsed ? "nav-collapsed" : ""}`}>
      <aside className="sidebar">
        <div className="brand">
          <Database size={26} />
          <div>
            <h1>Recruiter Console</h1>
            <p>Resume intelligence</p>
          </div>
          <button className="nav-collapse-toggle" type="button" onClick={() => setCollapsed((current) => !current)} title={collapsed ? "Expand navigation" : "Collapse navigation"}>
            {collapsed ? <PanelLeftOpen size={19} /> : <PanelLeftClose size={19} />}
          </button>
        </div>
        <nav className="nav-list">
          {navItems.map((item) => (
            <button key={item.key} className={page === item.key ? "is-active" : ""} onClick={() => onPageChange(item.key)} title={item.label}>
              {item.icon}
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Button icon={<RefreshCw size={18} />} onClick={onRefresh} disabled={busy} title="Refresh">
            Refresh
          </Button>
        </div>
      </aside>
      <section className="workspace">{children}</section>
    </main>
  );
}
