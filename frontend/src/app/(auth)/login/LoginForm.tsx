"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";

import { useAuth } from "@/context/AuthContext";

export default function LoginForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const next = searchParams.get("next");
  const { status, logIn } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (status === "authenticated") {
      router.replace(next ?? "/dashboard");
    }
  }, [status, next, router]);

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting || !email.trim() || !password) {
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      await logIn(email.trim(), password);
      router.replace(next ?? "/dashboard");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
      setSubmitting(false);
    }
  };

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Log in</h1>
        <p>Sign in to continue your interview practice.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <label className="label" htmlFor="email">
          Email
        </label>
        <input
          id="email"
          className="field"
          type="email"
          autoComplete="email"
          value={email}
          onChange={(event) => setEmail(event.target.value)}
          disabled={submitting}
          required
        />

        <label className="label" htmlFor="password">
          Password
        </label>
        <input
          id="password"
          className="field"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={submitting}
          required
        />

        {errorMessage && <div className="error-banner" role="alert">{errorMessage}</div>}

        <div className="actions">
          <button type="submit" className="button" disabled={submitting || !email.trim() || !password}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Signing in…" : "Log in"}
          </button>
        </div>
      </form>

      <p className="progress-label">
        Don&apos;t have an account? <Link href="/signup">Sign up</Link>
      </p>
    </main>
  );
}
