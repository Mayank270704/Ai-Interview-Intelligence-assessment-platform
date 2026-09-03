"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/services/api/client";
import type { CandidateKnowledgeState, GeneratedQuestion, QuestionDifficulty } from "@/services/api/types";
import { getInterview, submitAnswer } from "@/services/interview";

export type InterviewStatus = "loading" | "ready" | "submitting" | "error" | "not_found";

interface InterviewSessionState {
  status: InterviewStatus;
  question: GeneratedQuestion | null;
  turnId: string | null;
  turnNumber: number;
  difficulty: QuestionDifficulty | null;
  knowledgeState: CandidateKnowledgeState | null;
  completed: boolean;
  errorMessage: string | null;
}

const initialState: InterviewSessionState = {
  status: "loading",
  question: null,
  turnId: null,
  turnNumber: 0,
  difficulty: null,
  knowledgeState: null,
  completed: false,
  errorMessage: null,
};

export function useInterview(interviewId: string | null) {
  const [state, setState] = useState<InterviewSessionState>(initialState);

  const load = useCallback(async () => {
    if (!interviewId) {
      return;
    }
    setState((previous) => ({ ...previous, status: "loading", errorMessage: null }));
    try {
      const interview = await getInterview(interviewId);
      const pendingTurn = [...interview.turns].reverse().find((turn) => turn.answer === null);
      setState({
        status: "ready",
        question: interview.current_question,
        turnId: pendingTurn?.id ?? null,
        turnNumber: interview.turns.length,
        difficulty: interview.difficulty,
        knowledgeState: interview.knowledge_state,
        completed: interview.status === "completed",
        errorMessage: null,
      });
    } catch (error) {
      const isNotFound = error instanceof ApiError && error.status === 404;
      setState({
        ...initialState,
        status: isNotFound ? "not_found" : "error",
        errorMessage: error instanceof Error ? error.message : "Something went wrong.",
      });
    }
  }, [interviewId]);

  useEffect(() => {
    load();
  }, [load]);

  const answer = useCallback(
    async (answerText: string): Promise<boolean> => {
      if (!interviewId || !state.turnId || state.status === "submitting") {
        return false;
      }
      setState((previous) => ({ ...previous, status: "submitting", errorMessage: null }));
      try {
        const result = await submitAnswer(interviewId, state.turnId, answerText);
        setState((previous) => ({
          status: "ready",
          question: result.next_question,
          turnId: result.next_turn_id,
          turnNumber: result.answered_turn.turn_number + 1,
          difficulty: result.difficulty,
          knowledgeState: result.knowledge_state,
          completed: previous.completed,
          errorMessage: null,
        }));
        return true;
      } catch (error) {
        setState((previous) => ({
          ...previous,
          status: "error",
          errorMessage: error instanceof Error ? error.message : "Something went wrong.",
        }));
        return false;
      }
    },
    [interviewId, state.turnId, state.status]
  );

  return { ...state, submitAnswer: answer, retry: load };
}
