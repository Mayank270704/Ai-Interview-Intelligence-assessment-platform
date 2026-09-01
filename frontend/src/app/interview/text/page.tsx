import { Suspense } from "react";

import InterviewTextSession from "./InterviewTextSession";

export default function TextInterviewPage() {
  return (
    <Suspense fallback={<main className="narrow">Loading…</main>}>
      <InterviewTextSession />
    </Suspense>
  );
}
