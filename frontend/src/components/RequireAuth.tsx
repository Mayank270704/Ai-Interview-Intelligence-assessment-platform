"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

import { useAuth } from "@/context/AuthContext";

/**
 * Client-side route guard. The bearer token lives in browser storage, so the
 * server cannot make this decision in middleware -- the guard runs here and
 * sends anonymous visitors to the login page, preserving where they were going.
 */
export default function RequireAuth({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status !== "anonymous") {
      return;
    }
    const next = `${window.location.pathname}${window.location.search}`;
    router.replace(`/login?next=${encodeURIComponent(next)}`);
  }, [status, router]);

  if (status === "loading") {
    return (
      <main className="narrow">
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Checking your session…
        </p>
      </main>
    );
  }

  if (status === "anonymous") {
    return (
      <main className="narrow">
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Redirecting you to sign in…
        </p>
      </main>
    );
  }

  return <>{children}</>;
}
