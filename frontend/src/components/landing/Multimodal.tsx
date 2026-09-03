import InterviewerAvatar from "@/components/avatar/InterviewerAvatar";

import { Reveal } from "./motion";

export default function Multimodal() {
  return (
    <section className="lp-section lp-section--tint" id="intelligence">
      <div className="lp-shell">
        <Reveal>
          <span className="lp-eyebrow">Multimodal interviews</span>
          <h2 style={{ marginTop: 16, fontSize: "clamp(1.95rem, 4vw, 3.05rem)", fontWeight: 600 }}>
            One intelligence engine.
            <br />
            Three ways to interview.
          </h2>
          <p className="lp-lede" style={{ marginTop: 18 }}>
            The same reasoning drives every format. Choose the one that matches how you want to
            practise.
          </p>
        </Reveal>

        <div className="lp-modes">
          <Reveal index={0}>
            <article className="lp-mode">
            <span className="lp-mode-kind">TEXT</span>
            <h3>Focused conversational interview</h3>
            <p>Type your answers and read every follow-up at your own pace.</p>
            <div className="lp-mode-stage">
              <div className="lp-chatline">
                <b>AI</b>
                <span>How did you evaluate retrieval quality?</span>
              </div>
              <div className="lp-chatline" data-role="you">
                <b>YOU</b>
                <span>I compared recall@k against a keyword baseline…</span>
              </div>
            </div>
            </article>
          </Reveal>

          <Reveal index={1}>
            <article className="lp-mode">
            <span className="lp-mode-kind">VOICE</span>
            <h3>Speak naturally with the AI interviewer</h3>
            <p>The interviewer asks aloud, listens, and answers back in voice.</p>
            <div className="lp-mode-stage">
              <InterviewerAvatar state="listening" label="Listening" />
              <span className="lp-listening">RECORDING</span>
              <div className="lp-wave" role="img" aria-label="Microphone input level">
                {Array.from({ length: 22 }, (_, index) => (
                  <i key={index} style={{ "--lp-i": index } as React.CSSProperties} />
                ))}
              </div>
            </div>
            </article>
          </Reveal>

          <Reveal index={2}>
            <article className="lp-mode">
            <span className="lp-mode-kind">VIDEO</span>
            <h3>Face-to-face interview experience</h3>
            <p>Record your answer on camera while the interviewer responds.</p>
            <div className="lp-mode-stage">
              <div className="lp-camera" aria-hidden="true">
                <span className="lp-camera-figure" />
              </div>
              <InterviewerAvatar state="speaking" label="Interviewer" />
            </div>
            </article>
          </Reveal>
        </div>

        <p className="lp-note" style={{ marginTop: 20 }}>
          Interface previews are illustrative.
        </p>
      </div>
    </section>
  );
}
