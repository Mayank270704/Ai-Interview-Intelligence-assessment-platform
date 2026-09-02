import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";

import InterviewSetupForm from "./InterviewSetupForm";

export default function InterviewSetupPage() {
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
        <InterviewSetupForm />
      </Suspense>
    </RequireAuth>
  );
}
