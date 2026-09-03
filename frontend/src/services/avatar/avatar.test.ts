import assert from "node:assert/strict";
import { test } from "node:test";

import {
  AVATAR_STATES,
  type AvatarLifecycle,
  describeAvatarState,
  deriveAvatarState,
} from "./index.ts";

const RESTING: AvatarLifecycle = {
  completed: false,
  speaking: false,
  recording: false,
  submitting: false,
  preparing: false,
};

const lifecycle = (overrides: Partial<AvatarLifecycle> = {}): AvatarLifecycle => ({
  ...RESTING,
  ...overrides,
});

test("rests in idle when nothing is happening", () => {
  assert.equal(deriveAvatarState(RESTING), "idle");
});

test("speaks while question audio plays", () => {
  assert.equal(deriveAvatarState(lifecycle({ speaking: true })), "speaking");
});

test("listens while the candidate records", () => {
  assert.equal(deriveAvatarState(lifecycle({ recording: true })), "listening");
});

test("thinks while an answer is being evaluated", () => {
  assert.equal(deriveAvatarState(lifecycle({ submitting: true })), "thinking");
});

test("thinks while question audio is being fetched", () => {
  assert.equal(deriveAvatarState(lifecycle({ preparing: true })), "thinking");
});

test("a completed interview outranks every other signal", () => {
  const busy = lifecycle({
    completed: true,
    speaking: true,
    recording: true,
    submitting: true,
    preparing: true,
  });

  assert.equal(deriveAvatarState(busy), "completed");
});

test("audible speech outranks a pending request", () => {
  // The next question's audio starts while the submit round-trip is settling;
  // the avatar must speak rather than keep thinking.
  assert.equal(deriveAvatarState(lifecycle({ speaking: true, submitting: true })), "speaking");
});

test("recording outranks a pending request", () => {
  assert.equal(deriveAvatarState(lifecycle({ recording: true, preparing: true })), "listening");
});

test("walks the full interview turn: ask, listen, evaluate, ask again", () => {
  const observed = [
    lifecycle({ preparing: true }),
    lifecycle({ speaking: true }),
    RESTING,
    lifecycle({ recording: true }),
    lifecycle({ submitting: true }),
    lifecycle({ speaking: true }),
    lifecycle({ completed: true }),
  ].map(deriveAvatarState);

  assert.deepEqual(observed, [
    "thinking",
    "speaking",
    "idle",
    "listening",
    "thinking",
    "speaking",
    "completed",
  ]);
});

test("every state has a caption", () => {
  for (const state of AVATAR_STATES) {
    const label = describeAvatarState(state);
    assert.equal(typeof label, "string");
    assert.ok(label.length > 0, `${state} needs a caption`);
  }
});
