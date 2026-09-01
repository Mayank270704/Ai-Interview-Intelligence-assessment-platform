import { Suspense } from "react";

import InterviewSetupForm from "./InterviewSetupForm";

export default function InterviewSetupPage() {
  return (
    <Suspense fallback={<main className="narrow">Loading…</main>}>
      <InterviewSetupForm />
    </Suspense>
  );
}
