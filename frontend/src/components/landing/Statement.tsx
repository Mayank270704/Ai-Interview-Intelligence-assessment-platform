"use client";

import { useInView } from "./motion";

const VERBS = ["LISTENS", "REASONS", "ADAPTS", "EVALUATES"];

export default function Statement() {
  const { ref, inView } = useInView<HTMLElement>();

  return (
    <section
      className={`lp-section lp-statement ${inView ? "is-visible" : ""}`}
      ref={ref}
      id="platform"
    >
      <div className="lp-shell">
        <h2>Not another question bank.</h2>
        <p className="lp-statement-sub">
          An interview system that listens, reasons, adapts and evaluates.
        </p>

        <div className="lp-verbs">
          {VERBS.map((verb, index) => (
            <span className="lp-verb" key={verb} style={{ "--lp-i": index } as React.CSSProperties}>
              {verb}
            </span>
          ))}
        </div>

        <p className="lp-lede" style={{ margin: "38px auto 0", textAlign: "center" }}>
          Every answer changes what happens next.
        </p>
      </div>
    </section>
  );
}
