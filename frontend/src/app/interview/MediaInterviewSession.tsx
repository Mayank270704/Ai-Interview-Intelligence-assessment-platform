"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useRef, useState } from "react";

import { useMediaRecorder } from "@/hooks/useMediaRecorder";
import { ApiError } from "@/services/api/client";
import type {
  GeneratedQuestion,
  QuestionDifficulty,
  VideoAnswerResponse,
  VoiceAnswerResponse,
} from "@/services/api/types";
import { completeInterview, getInterview } from "@/services/interview";
import {
  audioObjectUrl,
  getQuestionAudio,
  submitVideoAnswer,
  submitVoiceAnswer,
} from "@/services/voice";

type SessionStatus = "loading" | "ready" | "submitting" | "error" | "not_found";

export type InterviewMode = "voice" | "video";

const COPY: Record<InterviewMode, { title: string; recordLabel: string; recordingLabel: string }> = {
  voice: {
    title: "Voice interview",
    recordLabel: "Record answer",
    recordingLabel: "Recording — click stop when you're done",
  },
  video: {
    title: "Video interview",
    recordLabel: "Record video answer",
    recordingLabel: "Recording — click stop when you're done",
  },
};

export default function MediaInterviewSession({ mode }: { mode: InterviewMode }) {
  const router = useRouter();
  const searchParams = useSearchParams();
  const interviewId = searchParams.get("interviewId");
  const copy = COPY[mode];

  const [status, setStatus] = useState<SessionStatus>("loading");
  const [question, setQuestion] = useState<GeneratedQuestion | null>(null);
  const [turnId, setTurnId] = useState<string | null>(null);
  const [turnNumber, setTurnNumber] = useState(0);
  const [difficulty, setDifficulty] = useState<QuestionDifficulty | null>(null);
  const [transcript, setTranscript] = useState<string | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [playingQuestion, setPlayingQuestion] = useState(false);
  const [ending, setEnding] = useState(false);
  const [completed, setCompleted] = useState(false);

  const recorder = useMediaRecorder(mode === "video");
  const previewRef = useRef<HTMLVideoElement | null>(null);
  const audioUrlRef = useRef<string | null>(null);

  const revokeAudioUrl = useCallback(() => {
    if (audioUrlRef.current) {
      URL.revokeObjectURL(audioUrlRef.current);
      audioUrlRef.current = null;
    }
  }, []);

  useEffect(() => revokeAudioUrl, [revokeAudioUrl]);

  useEffect(() => {
    if (previewRef.current && recorder.stream) {
      previewRef.current.srcObject = recorder.stream;
    }
  }, [recorder.stream]);

  const load = useCallback(async () => {
    if (!interviewId) {
      return;
    }
    setStatus("loading");
    setErrorMessage(null);
    try {
      const interview = await getInterview(interviewId);
      const pendingTurn = [...interview.turns].reverse().find((turn) => turn.answer === null);
      setQuestion(interview.current_question);
      setTurnId(pendingTurn?.id ?? null);
      setTurnNumber(interview.turns.length);
      setDifficulty(interview.difficulty);
      setCompleted(interview.status === "completed");
      setStatus("ready");
    } catch (error) {
      const isNotFound = error instanceof ApiError && error.status === 404;
      setStatus(isNotFound ? "not_found" : "error");
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
    }
  }, [interviewId]);

  useEffect(() => {
    load();
  }, [load]);

  const playAudio = useCallback(
    async (base64: string, mimeType: string) => {
      revokeAudioUrl();
      const url = audioObjectUrl(base64, mimeType);
      audioUrlRef.current = url;
      const audio = new Audio(url);
      await audio.play();
    },
    [revokeAudioUrl]
  );

  const handlePlayQuestion = async () => {
    if (!interviewId || playingQuestion) {
      return;
    }
    setPlayingQuestion(true);
    setErrorMessage(null);
    try {
      const audio = await getQuestionAudio(interviewId);
      await playAudio(audio.audio_base64, audio.audio_mime_type);
    } catch (error) {
      setErrorMessage(
        error instanceof Error ? error.message : "We couldn't play the question audio."
      );
    } finally {
      setPlayingQuestion(false);
    }
  };

  const handleStartRecording = async () => {
    setErrorMessage(null);
    setTranscript(null);
    await recorder.start();
  };

  const applyAnswerResult = (result: VideoAnswerResponse | VoiceAnswerResponse) => {
    setTranscript(result.transcribed_answer);
    setQuestion(result.next_question);
    setTurnId(result.next_turn_id);
    setTurnNumber(result.answered_turn.turn_number + 1);
    setDifficulty(result.difficulty);
    setStatus("ready");
  };

  const handleStopRecording = async () => {
    if (!interviewId || !turnId) {
      return;
    }
    const blob = await recorder.stop();
    if (!blob) {
      setErrorMessage("We didn't capture any audio. Please try recording again.");
      return;
    }

    setStatus("submitting");
    try {
      if (mode === "video") {
        const result = await submitVideoAnswer(interviewId, turnId, blob);
        applyAnswerResult(result);
      } else {
        const result = await submitVoiceAnswer(interviewId, turnId, blob);
        applyAnswerResult(result);
        if (result.next_question_audio_base64 && result.next_question_audio_mime_type) {
          try {
            await playAudio(result.next_question_audio_base64, result.next_question_audio_mime_type);
          } catch {
            // Autoplay can be blocked until the user interacts; the Play button still works.
          }
        }
      }
    } catch (error) {
      setStatus("error");
      setErrorMessage(error instanceof Error ? error.message : "Something went wrong.");
    }
  };

  const handleEndInterview = async () => {
    if (!interviewId || ending) {
      return;
    }
    setEnding(true);
    try {
      await completeInterview(interviewId);
    } catch {
      // An already-completed interview still has results worth showing.
    }
    router.push(`/results?interviewId=${interviewId}`);
  };

  if (!interviewId) {
    return (
      <main className="narrow">
        <h1>{copy.title}</h1>
        <div className="error-banner" role="alert">No interview was specified.</div>
      </main>
    );
  }

  if (status === "not_found") {
    return (
      <main className="narrow">
        <h1>Interview not found</h1>
        <div className="error-banner" role="alert">
          This interview could not be found. It may have expired or the link is invalid.
        </div>
      </main>
    );
  }

  if (status === "loading" && !question) {
    return (
      <main className="narrow">
        <h1>{copy.title}</h1>
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Loading your interview…
        </p>
      </main>
    );
  }

  const recording = recorder.status === "recording";
  const submitting = status === "submitting";
  const busy = submitting || ending;
  const canAnswer = Boolean(question) && Boolean(turnId) && !completed;

  return (
    <main className="narrow">
      <h1>{copy.title}</h1>
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
          <div className="actions">
            <button
              type="button"
              className="button secondary"
              onClick={handlePlayQuestion}
              disabled={playingQuestion || busy || recording}
            >
              {playingQuestion && <span className="spinner" aria-hidden="true" />}
              {playingQuestion ? "Loading audio…" : "Play question"}
            </button>
          </div>
        </div>
      )}

      {mode === "video" && recorder.stream && (
        <video className="media-preview" ref={previewRef} autoPlay muted playsInline />
      )}

      {recording && (
        <p className="progress-label">
          <span className="recording-dot" aria-hidden="true" />
          {copy.recordingLabel}
        </p>
      )}

      {submitting && (
        <p className="progress-label">
          <span className="spinner" aria-hidden="true" />
          Transcribing and analysing your answer…
        </p>
      )}

      {transcript && !submitting && (
        <div className="transcript-note">
          <strong>We heard:</strong> {transcript}
        </div>
      )}

      {(errorMessage || recorder.errorMessage) && (
        <div className="error-banner" role="alert">
          {errorMessage ?? recorder.errorMessage}
          {status === "error" && (
            <>
              {" "}
              <button type="button" className="button secondary" onClick={() => load()}>
                Retry
              </button>
            </>
          )}
        </div>
      )}

      <div className="actions">
        {recording ? (
          <button type="button" className="button" onClick={handleStopRecording} disabled={busy}>
            Stop and submit
          </button>
        ) : (
          <button
            type="button"
            className="button"
            onClick={handleStartRecording}
            disabled={busy || !canAnswer}
          >
            {copy.recordLabel}
          </button>
        )}
        <button type="button" className="button secondary" onClick={handleEndInterview} disabled={busy || recording}>
          {ending ? "Finishing…" : completed ? "View results" : "End Interview"}
        </button>
      </div>
    </main>
  );
}
