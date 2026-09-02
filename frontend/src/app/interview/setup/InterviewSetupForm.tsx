"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useState } from "react";

import type { QuestionDifficulty } from "@/services/api/types";
import { startInterview } from "@/services/interview";

type InterviewMode = "text" | "voice" | "video";

export default function InterviewSetupForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resumeId = searchParams.get("resumeId");

  const [objective, setObjective] = useState("");
  const [difficulty, setDifficulty] = useState<QuestionDifficulty>("medium");
  const [mode, setMode] = useState<InterviewMode>("text");
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!resumeId) {
    return (
      <main className="narrow">
        <h1>Interview setup</h1>
        <div className="error-banner">No resume was found for this session. Please upload your resume again.</div>
      </main>
    );
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!objective.trim() || submitting) {
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);

    try {
      const question = await startInterview(resumeId, objective.trim(), difficulty);
      router.push(`/interview/${mode}?interviewId=${question.interview_id}`);
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
      setSubmitting(false);
    }
  };

  return (
    <main className="narrow">
      <div className="page-header">
        <h1>Set up your interview</h1>
        <p>Tell us what role or topic this interview should focus on.</p>
      </div>

      <form onSubmit={handleSubmit}>
        <label className="label" htmlFor="objective">
          Interview objective
        </label>
        <input
          id="objective"
          className="field"
          type="text"
          placeholder="e.g. Machine Learning Engineer"
          value={objective}
          onChange={(event) => setObjective(event.target.value)}
          disabled={submitting}
          required
        />

        <label className="label" htmlFor="difficulty">
          Difficulty
        </label>
        <select
          id="difficulty"
          className="field"
          value={difficulty}
          onChange={(event) => setDifficulty(event.target.value as QuestionDifficulty)}
          disabled={submitting}
        >
          <option value="easy">Easy</option>
          <option value="medium">Medium</option>
          <option value="hard">Hard</option>
        </select>

        <label className="label" htmlFor="mode">
          Interview format
        </label>
        <select
          id="mode"
          className="field"
          value={mode}
          onChange={(event) => setMode(event.target.value as InterviewMode)}
          disabled={submitting}
        >
          <option value="text">Text — type your answers</option>
          <option value="voice">Voice — speak your answers</option>
          <option value="video">Video — record yourself answering</option>
        </select>

        {errorMessage && <div className="error-banner">{errorMessage}</div>}

        <div className="actions">
          <button type="submit" className="button" disabled={submitting || !objective.trim()}>
            {submitting && <span className="spinner" aria-hidden="true" />}
            {submitting ? "Starting interview…" : "Start Interview"}
          </button>
        </div>
      </form>
    </main>
  );
}
