import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";

import ResultsSummary from "./ResultsSummary";

export default function ResultsPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="narrow">
            <p className="progress-label">
              <span className="spinner" aria-hidden="true" />
              Loading…
            </p>
          </main>
        }
      >
        <ResultsSummary />
      </Suspense>
    </RequireAuth>
  );
}
