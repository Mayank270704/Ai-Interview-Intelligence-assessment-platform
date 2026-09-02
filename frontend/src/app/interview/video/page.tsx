import { Suspense } from "react";

import RequireAuth from "@/components/RequireAuth";
import MediaInterviewSession from "../MediaInterviewSession";

export default function VideoInterviewPage() {
  return (
    <RequireAuth>
      <Suspense
        fallback={
          <main className="narrow">
            <h1>Video interview</h1>
            <p className="progress-label">
              <span className="spinner" aria-hidden="true" />
              Loading…
            </p>
          </main>
        }
      >
        <MediaInterviewSession mode="video" />
      </Suspense>
    </RequireAuth>
  );
}
