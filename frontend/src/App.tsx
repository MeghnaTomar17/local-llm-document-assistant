import { useEffect, useState } from "react";
import { AppLayout, type PageKey } from "./components/layout/AppLayout";
import { Loader } from "./components/ui/Loader";
import { SkeletonBlock } from "./components/ui/Skeleton";
import { AppProvider, useAppData } from "./context/AppContext";
import { DashboardPage } from "./pages/DashboardPage";
import { SearchPage } from "./pages/SearchPage";
import { SessionsPage } from "./pages/SessionsPage";

function AppContent() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const { loading, busy, error, notice, refresh, clearError, setNotice } = useAppData();

  useEffect(() => {
    if (!notice) return;
    const timer = window.setTimeout(() => setNotice(""), 5500);
    return () => window.clearTimeout(timer);
  }, [notice, setNotice]);

  if (loading) {
    return (
      <main className="center-screen">
        <Loader label="Loading recruiter workspace..." />
        <div className="startup-skeletons" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, index) => (
            <SkeletonBlock className="skeleton-card" key={index} />
          ))}
        </div>
      </main>
    );
  }

  return (
    <AppLayout
      page={page}
      onPageChange={(nextPage) => {
        setNotice("");
        setPage(nextPage);
      }}
      onRefresh={refresh}
      busy={busy}
    >
      {error && (
        <button className="error-banner action-banner" onClick={clearError}>
          {error}
        </button>
      )}
      {notice && (
        <button className="success-banner action-banner" onClick={() => setNotice("")}>
          {notice}
        </button>
      )}
      {page === "dashboard" && <DashboardPage />}
      {page === "sessions" && <SessionsPage />}
      {page === "search" && <SearchPage />}
    </AppLayout>
  );
}

export default function App() {
  return (
    <AppProvider>
      <AppContent />
    </AppProvider>
  );
}
