import { Suspense } from "react";

import ResultsSummary from "./ResultsSummary";

export default function ResultsPage() {
  return (
    <Suspense fallback={<main className="narrow">Loading…</main>}>
      <ResultsSummary />
    </Suspense>
  );
}
