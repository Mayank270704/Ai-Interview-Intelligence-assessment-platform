import { apiRequest } from "@/services/api/client";
import type {
  QuestionAudioResponse,
  VideoAnswerResponse,
  VoiceAnswerResponse,
} from "@/services/api/types";

export async function getQuestionAudio(interviewId: string): Promise<QuestionAudioResponse> {
  return apiRequest<QuestionAudioResponse>(`/interviews/${interviewId}/question-audio`);
}

export async function submitVoiceAnswer(
  interviewId: string,
  turnId: string,
  audio: Blob,
  fileName = "answer.webm"
): Promise<VoiceAnswerResponse> {
  const formData = new FormData();
  formData.append("turn_id", turnId);
  formData.append("file", audio, fileName);

  return apiRequest<VoiceAnswerResponse>(`/interviews/${interviewId}/voice-answers`, {
    method: "POST",
    body: formData,
  });
}

export async function submitVideoAnswer(
  interviewId: string,
  turnId: string,
  video: Blob,
  fileName = "answer.webm"
): Promise<VideoAnswerResponse> {
  const formData = new FormData();
  formData.append("turn_id", turnId);
  formData.append("file", video, fileName);

  return apiRequest<VideoAnswerResponse>(`/interviews/${interviewId}/video-answers`, {
    method: "POST",
    body: formData,
  });
}

function decodeBase64(base64: string): Uint8Array<ArrayBuffer> {
  const binary = window.atob(base64);
  const bytes = new Uint8Array(new ArrayBuffer(binary.length));
  for (let index = 0; index < binary.length; index += 1) {
    bytes[index] = binary.charCodeAt(index);
  }
  return bytes;
}

/** Raw 16-bit PCM (what Gemini TTS returns) is not playable by browsers as-is. */
function isRawPcm(mimeType: string): boolean {
  const normalized = mimeType.toLowerCase();
  return normalized.includes("l16") || normalized.includes("pcm");
}

function sampleRateFrom(mimeType: string): number {
  const match = /rate=(\d+)/i.exec(mimeType);
  return match ? Number(match[1]) : 24000;
}

/** Wrap raw mono 16-bit PCM samples in a minimal WAV container so <audio> can play them. */
function wavFromPcm(pcm: Uint8Array, sampleRate: number): Uint8Array<ArrayBuffer> {
  const channels = 1;
  const bitsPerSample = 16;
  const blockAlign = (channels * bitsPerSample) / 8;
  const byteRate = sampleRate * blockAlign;
  const buffer = new ArrayBuffer(44 + pcm.length);
  const view = new DataView(buffer);

  const writeAscii = (offset: number, text: string) => {
    for (let index = 0; index < text.length; index += 1) {
      view.setUint8(offset + index, text.charCodeAt(index));
    }
  };

  writeAscii(0, "RIFF");
  view.setUint32(4, 36 + pcm.length, true);
  writeAscii(8, "WAVE");
  writeAscii(12, "fmt ");
  view.setUint32(16, 16, true); // PCM subchunk size
  view.setUint16(20, 1, true); // audio format: PCM
  view.setUint16(22, channels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);
  writeAscii(36, "data");
  view.setUint32(40, pcm.length, true);

  const wav = new Uint8Array(buffer);
  wav.set(pcm, 44);
  return wav;
}

/** Turn a base64 audio payload from the API into a playable object URL. */
export function audioObjectUrl(base64: string, mimeType: string): string {
  const bytes = decodeBase64(base64);
  if (isRawPcm(mimeType)) {
    const wav = wavFromPcm(bytes, sampleRateFrom(mimeType));
    return URL.createObjectURL(new Blob([wav], { type: "audio/wav" }));
  }
  return URL.createObjectURL(new Blob([bytes], { type: mimeType }));
}
