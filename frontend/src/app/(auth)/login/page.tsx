import { Suspense } from "react";

import LoginForm from "./LoginForm";

export default function LoginPage() {
  return (
    <Suspense
      fallback={
        <main className="narrow">
          <h1>Log in</h1>
          <p className="progress-label">
            <span className="spinner" aria-hidden="true" />
            Loading…
          </p>
        </main>
      }
    >
      <LoginForm />
    </Suspense>
  );
}
