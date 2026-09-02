import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";

import InterviewTextSession from "./InterviewTextSession";

export default function TextInterviewPage() {
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
        <InterviewTextSession />
      </Suspense>
    </RequireAuth>
  );
}
