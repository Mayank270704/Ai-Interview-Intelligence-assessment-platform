import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";
import MediaInterviewSession from "../MediaInterviewSession";

export default function VoiceInterviewPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="narrow">
            <h1>Voice interview</h1>
            <p className="progress-label">
              <span className="spinner" aria-hidden="true" />
              Loading…
            </p>
          </main>
        }
      >
        <MediaInterviewSession mode="voice" />
      </Suspense>
    </RequireAuth>
  );
}
