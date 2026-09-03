/**
 * Avatar presentation state.
 *
 * The avatar is a *view* of the interview lifecycle: it owns no interview logic
 * and makes no claim to analyse the candidate. Every state here is derived from
 * signals the session already tracks (audio playback, recording, request
 * in-flight), so the avatar can never disagree with the interview it depicts.
 */
export type AvatarState = "idle" | "speaking" | "listening" | "thinking" | "completed";

export const AVATAR_STATES: readonly AvatarState[] = [
  "idle",
  "speaking",
  "listening",
  "thinking",
  "completed",
];

/** Signals the interview session already has; none of them are avatar-specific. */
export interface AvatarLifecycle {
  /** The interview is finished; no further answers are accepted. */
  completed: boolean;
  /** Synthesized question audio is currently playing. */
  speaking: boolean;
  /** The candidate is recording an answer. */
  recording: boolean;
  /** An answer is with the backend for analysis and evaluation. */
  submitting: boolean;
  /** Question audio is being fetched, or the session is still loading. */
  preparing: boolean;
}

/**
 * Map the interview lifecycle onto a single avatar state.
 *
 * Order matters: a completed interview outranks everything so the avatar can
 * never look mid-conversation after the fact, and actual audio playback outranks
 * the request flags so the avatar speaks exactly while sound is audible.
 */
export function deriveAvatarState(lifecycle: AvatarLifecycle): AvatarState {
  if (lifecycle.completed) {
    return "completed";
  }
  if (lifecycle.speaking) {
    return "speaking";
  }
  if (lifecycle.recording) {
    return "listening";
  }
  if (lifecycle.submitting || lifecycle.preparing) {
    return "thinking";
  }
  return "idle";
}

const STATE_LABELS: Record<AvatarState, string> = {
  idle: "Ready",
  speaking: "Asking the question",
  listening: "Listening to your answer",
  thinking: "Reviewing your answer",
  completed: "Interview complete",
};

/** Short caption announced to assistive technology and shown under the avatar. */
export function describeAvatarState(state: AvatarState): string {
  return STATE_LABELS[state];
}
