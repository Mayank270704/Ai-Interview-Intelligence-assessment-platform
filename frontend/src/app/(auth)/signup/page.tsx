"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { useAuth } from "@/context/AuthContext";

const MIN_PASSWORD_LENGTH = 8;

export default function SignupPage() {
  const router = useRouter();
  const { signUp } = useAuth();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [confirmationRequired, setConfirmationRequired] = useState(false);

  const passwordTooShort = password.length > 0 && password.length < MIN_PASSWORD_LENGTH;

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (submitting || !email.trim() || password.length < MIN_PASSWORD_LENGTH) {
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      const outcome = await signUp(email.trim(), password);
      if (outcome.emailConfirmationRequired) {
        setConfirmationRequired(true);
        setSubmitting(false);
        return;
      }
      router.replace("/dashboard");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
      setSubmitting(false);
    }
  };

  if (confirmationRequired) {
    return (
      <main className="narrow">
        <div className="page-header">
          <h1>Confirm your email</h1>
          <p>
            We sent a confirmation link to <strong>{email}</strong>. Confirm your address, then log in
            to get started.
          </p>
        </div>
        <div className="actions">
          <Link href="/login" className="button">
            Go to log in
          </Link>
        </div>
      </main>
    );
  }

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Sign up</h1>
        <p>Create an account to upload your resume and start practicing.</p>
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
          autoComplete="new-password"
          minLength={MIN_PASSWORD_LENGTH}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          disabled={submitting}
          required
        />
        <p className="progress-label">At least {MIN_PASSWORD_LENGTH} characters.</p>

        {passwordTooShort && (
          <div className="error-banner" role="alert">Your password must be at least {MIN_PASSWORD_LENGTH} characters.</div>
        )}
        {errorMessage && <div className="error-banner" role="alert">{errorMessage}</div>}

        <div className="actions">
          <button
            type="submit"
            className="button"
            disabled={submitting || !email.trim() || password.length < MIN_PASSWORD_LENGTH}
          >
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Creating account…" : "Sign up"}
          </button>
        </div>
      </form>

      <p className="progress-label">
        Already have an account? <Link href="/login">Log in</Link>
      </p>
    </main>
  );
}
