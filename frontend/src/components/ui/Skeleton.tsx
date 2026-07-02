export function SkeletonBlock({ className = "" }: { className?: string }) {
  return <div className={`skeleton ${className}`.trim()} aria-hidden="true" />;
}

export function SkeletonRows({ count = 5 }: { count?: number }) {
  return (
    <div className="skeleton-stack" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <SkeletonBlock className="skeleton-row" key={index} />
      ))}
    </div>
  );
}

export function SessionSkeletons({ count = 9 }: { count?: number }) {
  return (
    <div className="session-list" aria-hidden="true">
      {Array.from({ length: count }).map((_, index) => (
        <div className="session-row skeleton-session" key={index}>
          <SkeletonBlock className="skeleton-line skeleton-line-strong" />
          <SkeletonBlock className="skeleton-line skeleton-line-short" />
          <SkeletonBlock className="skeleton-line skeleton-line-medium" />
        </div>
      ))}
    </div>
  );
}

export function WorkspaceSkeleton() {
  return (
    <section className="workspace-panel workspace-skeleton" aria-hidden="true">
      <div className="workspace-heading">
        <div className="candidate-title">
          <SkeletonBlock className="skeleton-avatar" />
          <div className="skeleton-fill">
            <SkeletonBlock className="skeleton-line skeleton-line-title" />
            <SkeletonBlock className="skeleton-line skeleton-line-medium" />
            <div className="panel-badges">
              <SkeletonBlock className="skeleton-pill" />
              <SkeletonBlock className="skeleton-pill" />
              <SkeletonBlock className="skeleton-pill" />
            </div>
          </div>
        </div>
      </div>
      <SkeletonBlock className="skeleton-tabs" />
      <div className="resume-summary-grid">
        {Array.from({ length: 6 }).map((_, index) => (
          <SkeletonBlock className="skeleton-card" key={index} />
        ))}
      </div>
      <SkeletonBlock className="skeleton-large" />
    </section>
  );
}
