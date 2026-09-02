import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";
import ResumeAnalysis from "./ResumeAnalysis";

export default function ResumeAnalysisPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="narrow">
            <h1>Resume analysis</h1>
            <p className="progress-label">
              <span className="spinner" aria-hidden="true" />
              Loading…
            </p>
          </main>
        }
      >
        <ResumeAnalysis />
      </Suspense>
    </RequireAuth>
  );
}
