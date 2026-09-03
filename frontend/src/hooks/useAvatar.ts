"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  type AvatarState,
  describeAvatarState,
  deriveAvatarState,
} from "@/services/avatar";

/** Interview signals the avatar reflects. `speaking` is measured, not passed in. */
export interface UseAvatarOptions {
  completed: boolean;
  recording: boolean;
  submitting: boolean;
  preparing: boolean;
}

export interface UseAvatarResult {
  state: AvatarState;
  label: string;
  /** True while question audio is actually audible. */
  speaking: boolean;
  /** Attach to the avatar root; the mouth reads its `--avatar-level`. */
  avatarRef: React.RefObject<HTMLDivElement | null>;
  /** The element to play question audio through, once registered. */
  audioRef: React.RefObject<HTMLAudioElement | null>;
  /**
   * Ref callback for the `<audio>` element. A callback rather than a plain ref
   * because the element mounts only once the session leaves its loading and
   * error branches, and the listeners have to follow it when it appears.
   */
  registerAudio: (node: HTMLAudioElement | null) => void;
}

/** Perceptual gain: speech RMS rarely exceeds ~0.3, so scale it into 0..1. */
const LEVEL_GAIN = 3.2;
/** Exponential smoothing keeps the mouth from flickering frame to frame. */
const LEVEL_SMOOTHING = 0.6;

/**
 * Derive the avatar's state from the interview lifecycle, and drive its mouth
 * from the amplitude of the question audio that is already playing.
 *
 * This is amplitude-reactive movement, not phoneme lip sync: the mouth opens in
 * proportion to how loud the speech is at that instant. The level is written
 * straight to a CSS custom property on the avatar element rather than to React
 * state, so a 60fps audio loop never re-renders the interview around it.
 *
 * Everything here is browser-native (Web Audio + CSS). No avatar service, asset
 * pipeline, or extra dependency is involved.
 */
export function useAvatar({
  completed,
  recording,
  submitting,
  preparing,
}: UseAvatarOptions): UseAvatarResult {
  const [speaking, setSpeaking] = useState(false);
  const [reducedMotion, setReducedMotion] = useState(false);
  const [audioNode, setAudioNode] = useState<HTMLAudioElement | null>(null);

  const avatarRef = useRef<HTMLDivElement | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const analyserRef = useRef<AnalyserNode | null>(null);
  const frameRef = useRef<number | null>(null);
  const levelRef = useRef(0);

  const registerAudio = useCallback((node: HTMLAudioElement | null) => {
    audioRef.current = node;
    setAudioNode(node);
  }, []);

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) {
      return;
    }
    const query = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(query.matches);
    const onChange = (event: MediaQueryListEvent) => setReducedMotion(event.matches);
    query.addEventListener("change", onChange);
    return () => query.removeEventListener("change", onChange);
  }, []);

  const writeLevel = useCallback((value: number) => {
    levelRef.current = value;
    avatarRef.current?.style.setProperty("--avatar-level", value.toFixed(3));
  }, []);

  /**
   * Route the audio element through an analyser. Only ever done once: a media
   * element can back a single MediaElementAudioSourceNode, and creating the
   * context needs the user gesture that started playback.
   */
  const ensureAnalyser = useCallback((): AnalyserNode | null => {
    if (analyserRef.current) {
      return analyserRef.current;
    }
    if (!audioNode || typeof window === "undefined") {
      return null;
    }
    const AudioCtor = window.AudioContext;
    if (!AudioCtor) {
      return null;
    }

    try {
      const context = new AudioCtor();
      const analyser = context.createAnalyser();
      analyser.fftSize = 256;
      analyser.smoothingTimeConstant = 0.75;
      // Creating the source reroutes the element's output, so it is connected
      // through to the speakers in the same breath or playback goes silent.
      const source = context.createMediaElementSource(audioNode);
      source.connect(analyser);
      analyser.connect(context.destination);

      contextRef.current = context;
      analyserRef.current = analyser;
      return analyser;
    } catch {
      // Web Audio is unavailable or the element is already routed. Playback is
      // untouched; the avatar falls back to its baseline speaking cadence.
      return null;
    }
  }, [audioNode]);

  useEffect(() => {
    if (!audioNode) {
      return;
    }
    const onPlaying = () => setSpeaking(true);
    const onStopped = () => setSpeaking(false);

    audioNode.addEventListener("playing", onPlaying);
    audioNode.addEventListener("pause", onStopped);
    audioNode.addEventListener("ended", onStopped);
    audioNode.addEventListener("emptied", onStopped);
    audioNode.addEventListener("error", onStopped);
    return () => {
      audioNode.removeEventListener("playing", onPlaying);
      audioNode.removeEventListener("pause", onStopped);
      audioNode.removeEventListener("ended", onStopped);
      audioNode.removeEventListener("emptied", onStopped);
      audioNode.removeEventListener("error", onStopped);
      setSpeaking(false);
    };
  }, [audioNode]);

  useEffect(() => {
    if (!speaking || reducedMotion) {
      writeLevel(0);
      return;
    }

    const analyser = ensureAnalyser();
    if (!analyser) {
      return;
    }
    void contextRef.current?.resume().catch(() => {
      // A suspended context only costs the mouth movement, never the audio.
    });

    const samples = new Uint8Array(analyser.fftSize);
    const tick = () => {
      analyser.getByteTimeDomainData(samples);
      let sumOfSquares = 0;
      for (let index = 0; index < samples.length; index += 1) {
        const deviation = (samples[index] - 128) / 128;
        sumOfSquares += deviation * deviation;
      }
      const amplitude = Math.min(1, Math.sqrt(sumOfSquares / samples.length) * LEVEL_GAIN);
      writeLevel(levelRef.current * LEVEL_SMOOTHING + amplitude * (1 - LEVEL_SMOOTHING));
      frameRef.current = window.requestAnimationFrame(tick);
    };
    frameRef.current = window.requestAnimationFrame(tick);

    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      writeLevel(0);
    };
  }, [speaking, reducedMotion, ensureAnalyser, writeLevel]);

  useEffect(() => {
    // The context outlives individual plays (the element can only be routed
    // once), so it is torn down with the component rather than per track.
    return () => {
      if (frameRef.current !== null) {
        window.cancelAnimationFrame(frameRef.current);
        frameRef.current = null;
      }
      void contextRef.current?.close().catch(() => {
        // Already closed by the browser during teardown.
      });
      contextRef.current = null;
      analyserRef.current = null;
    };
  }, []);

  const state = useMemo(
    () => deriveAvatarState({ completed, speaking, recording, submitting, preparing }),
    [completed, speaking, recording, submitting, preparing]
  );

  return {
    state,
    label: describeAvatarState(state),
    speaking,
    avatarRef,
    audioRef,
    registerAudio,
  };
}
