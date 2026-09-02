"use client";

import { useCallback, useEffect, useRef, useState } from "react";

export type RecorderStatus = "idle" | "requesting" | "recording" | "unsupported" | "denied";

const AUDIO_MIME_CANDIDATES = ["audio/webm", "audio/ogg", "audio/mp4"];
const VIDEO_MIME_CANDIDATES = ["video/webm", "video/mp4"];

function pickMimeType(candidates: string[]): string | null {
  if (typeof window === "undefined" || typeof window.MediaRecorder === "undefined") {
    return null;
  }
  return candidates.find((candidate) => MediaRecorder.isTypeSupported(candidate)) ?? null;
}

/**
 * Capture a microphone (and optionally camera) answer with the browser's own
 * MediaRecorder -- no third-party dependency. `stop()` resolves with the
 * recorded blob, tagged with a bare MIME type the API accepts.
 */
export function useMediaRecorder(withVideo: boolean) {
  const [status, setStatus] = useState<RecorderStatus>("idle");
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [stream, setStream] = useState<MediaStream | null>(null);

  const recorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  const releaseStream = useCallback(() => {
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    setStream(null);
  }, []);

  useEffect(() => releaseStream, [releaseStream]);

  const start = useCallback(async (): Promise<boolean> => {
    setErrorMessage(null);

    const mimeType = pickMimeType(withVideo ? VIDEO_MIME_CANDIDATES : AUDIO_MIME_CANDIDATES);
    if (!mimeType || typeof navigator === "undefined" || !navigator.mediaDevices) {
      setStatus("unsupported");
      setErrorMessage("Recording isn't supported in this browser. You can use the text interview instead.");
      return false;
    }

    setStatus("requesting");
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
        video: withVideo,
      });
      streamRef.current = mediaStream;
      setStream(mediaStream);

      const recorder = new MediaRecorder(mediaStream, { mimeType });
      chunksRef.current = [];
      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data.size > 0) {
          chunksRef.current.push(event.data);
        }
      };
      recorderRef.current = recorder;
      recorder.start();
      setStatus("recording");
      return true;
    } catch {
      releaseStream();
      setStatus("denied");
      setErrorMessage(
        withVideo
          ? "We couldn't access your camera and microphone. Check your browser permissions and try again."
          : "We couldn't access your microphone. Check your browser permissions and try again."
      );
      return false;
    }
  }, [withVideo, releaseStream]);

  const stop = useCallback((): Promise<Blob | null> => {
    const recorder = recorderRef.current;
    if (!recorder || recorder.state === "inactive") {
      return Promise.resolve(null);
    }

    const mimeType = recorder.mimeType.split(";")[0] || (withVideo ? "video/webm" : "audio/webm");

    return new Promise<Blob | null>((resolve) => {
      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: mimeType });
        chunksRef.current = [];
        recorderRef.current = null;
        releaseStream();
        setStatus("idle");
        resolve(blob.size > 0 ? blob : null);
      };
      recorder.stop();
    });
  }, [withVideo, releaseStream]);

  return { status, errorMessage, stream, start, stop };
}
