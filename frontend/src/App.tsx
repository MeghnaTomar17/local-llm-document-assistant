import { useState } from "react";
import { AppLayout, type PageKey } from "./components/layout/AppLayout";
import { Loader } from "./components/ui/Loader";
import { SkeletonBlock } from "./components/ui/Skeleton";
import { AppProvider, useAppData } from "./context/AppContext";
import { DashboardPage } from "./pages/DashboardPage";
import { SearchPage } from "./pages/SearchPage";
import { SessionsPage } from "./pages/SessionsPage";

function AppContent() {
  const [page, setPage] = useState<PageKey>("dashboard");
  const { loading, busy, error, notice, duplicateWarning, refresh, clearError, setNotice, clearDuplicateWarning } = useAppData();

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
    <AppLayout page={page} onPageChange={setPage} onRefresh={refresh} busy={busy}>
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
      {duplicateWarning && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <section className="duplicate-dialog">
            <h3>Candidate already exists</h3>
            <p>{duplicateWarning.message || "Candidate already exists."}</p>
            <dl>
              <div><dt>Name</dt><dd>{duplicateWarning.candidate_name || "-"}</dd></div>
              <div><dt>Email</dt><dd>{duplicateWarning.email || "-"}</dd></div>
              <div><dt>Phone</dt><dd>{duplicateWarning.phone || "-"}</dd></div>
            </dl>
            <button className="btn btn-primary" onClick={clearDuplicateWarning}>Got it</button>
          </section>
        </div>
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
