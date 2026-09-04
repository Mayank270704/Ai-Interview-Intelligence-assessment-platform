"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import { useInterview } from "@/hooks/useInterview";
import { ApiError } from "@/services/api/client";
import { completeInterview } from "@/services/interview";

export default function InterviewTextSession() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const interviewId = searchParams.get("interviewId");

  const { status, question, turnNumber, difficulty, completed, submitAnswer, errorMessage, retry } =
    useInterview(interviewId);
  const [answer, setAnswer] = useState("");
  const [ending, setEnding] = useState(false);

  if (!interviewId) {
    return (
      <main className="narrow">
        <h1>Interview</h1>
        <div className="error-banner" role="alert">No interview was specified.</div>
      </main>
    );
  }

  if (status === "not_found") {
    return (
      <main className="narrow">
        <h1>Interview not found</h1>
        <div className="error-banner" role="alert">This interview could not be found. It may have expired or the link is invalid.</div>
      </main>
    );
  }

  if (status === "loading" && !question) {
    return (
      <main className="narrow">
        <h1>Interview</h1>
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Loading your interview…
        </p>
      </main>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!answer.trim() || status === "submitting" || completed) {
      return;
    }
    const succeeded = await submitAnswer(answer.trim());
    if (succeeded) {
      setAnswer("");
    }
  };

  // Ending the interview closes it server-side, exactly as the voice and video
  // sessions do, so a text interview is not left in progress indefinitely.
  const handleEndInterview = async () => {
    if (ending) {
      return;
    }
    setEnding(true);
    try {
      await completeInterview(interviewId);
    } catch (error) {
      // An already-completed interview still has results worth showing.
      if (!(error instanceof ApiError)) {
        throw error;
      }
    }
    router.push(`/results?interviewId=${interviewId}`);
  };

  const submitting = status === "submitting";

  return (
    <main className="narrow">
      <h1>Interview</h1>
      {turnNumber > 0 && (
        <p className="progress-label">
          Question {turnNumber}
          {difficulty ? ` · Difficulty: ${difficulty}` : ""}
        </p>
      )}

      {completed && (
        <div className="card">
          <p>
            This interview is complete. Your results are ready.{" "}
            <Link href={`/results?interviewId=${interviewId}`}>View results</Link>
          </p>
        </div>
      )}

      {question && !completed && (
        <div className="card question-card">
          <p className="question-text">{question.question}</p>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <label className="label" htmlFor="answer">
          Your answer
        </label>
        <textarea
          id="answer"
          className="field"
          rows={6}
          value={answer}
          onChange={(event) => setAnswer(event.target.value)}
          disabled={submitting || !question || completed}
          placeholder="Type your answer here…"
        />

        {status === "error" && errorMessage && (
          <div className="error-banner" role="alert">
            {errorMessage}{" "}
            <button type="button" className="button secondary" onClick={() => retry()}>
              Retry
            </button>
          </div>
        )}

        <div className="actions">
          <button
            type="submit"
            className="button"
            disabled={submitting || !answer.trim() || !question || completed}
          >
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Submitting…" : "Submit Answer"}
          </button>
          <button
            type="button"
            className="button secondary"
            onClick={handleEndInterview}
            disabled={submitting || ending}
          >
            {ending ? "Finishing…" : completed ? "View results" : "End Interview"}
          </button>
        </div>
      </form>
    </main>
  );
}
