"use client";

import { useEffect, useRef, useState } from "react";

function prefersReducedMotion(): boolean {
  return (
    typeof window !== "undefined" &&
    typeof window.matchMedia === "function" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches
  );
}

/**
 * Reveal a section once, the first time it scrolls into view.
 *
 * One observer per section, disconnected as soon as it fires: the page never
 * holds a scroll listener or a running loop for entrance animation.
 */
export function useInView<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);
  const [inView, setInView] = useState(false);

  useEffect(() => {
    const node = ref.current;
    if (!node || inView) {
      return;
    }
    if (typeof IntersectionObserver === "undefined") {
      setInView(true);
      return;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries.some((entry) => entry.isIntersecting)) {
          setInView(true);
          observer.disconnect();
        }
      },
      // threshold 0 with a small absolute bottom margin: a ratio would be
      // unreachable for a section taller than the viewport, and a percentage
      // margin would exclude the foot of the page on a very tall screen.
      { threshold: 0, rootMargin: "0px 0px -60px 0px" }
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [inView]);

  return { ref, inView };
}

interface RevealProps {
  children: React.ReactNode;
  className?: string;
  /** Stagger position; drives the CSS transition delay. */
  index?: number;
  as?: "div" | "section" | "li";
}

/** Fades and lifts its children into place once, on first view. */
export function Reveal({ children, className = "", index, as = "div" }: RevealProps) {
  const { ref, inView } = useInView<HTMLDivElement>();
  const Tag = as;

  return (
    <Tag
      ref={ref as React.RefObject<never>}
      className={`lp-reveal ${inView ? "is-visible" : ""} ${className}`.trim()}
      style={index === undefined ? undefined : ({ "--lp-i": index } as React.CSSProperties)}
    >
      {children}
    </Tag>
  );
}

/**
 * Count a number up when it first becomes visible.
 *
 * Renders the final value immediately for reduced motion and before hydration,
 * so the number is never missing or wrong at rest.
 */
export function CountUp({
  to,
  active,
  duration = 1300,
}: {
  to: number;
  active: boolean;
  duration?: number;
}) {
  const [value, setValue] = useState(to);

  useEffect(() => {
    if (!active) {
      return;
    }
    if (prefersReducedMotion()) {
      setValue(to);
      return;
    }

    let frame = 0;
    const started = performance.now();
    const tick = (now: number) => {
      const progress = Math.min(1, (now - started) / duration);
      // Ease out, so the number settles rather than stopping dead.
      setValue(Math.round(to * (1 - Math.pow(1 - progress, 3))));
      if (progress < 1) {
        frame = requestAnimationFrame(tick);
      }
    };
    // Left at the final value until the first frame lands, so an environment
    // that never runs the callback shows the real number rather than zero.
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, [active, to, duration]);

  return <>{value}</>;
}

/**
 * Track the pointer across an element as two -1..1 values.
 *
 * Written straight to CSS custom properties on the node, so moving the mouse
 * never re-renders React. Ignored under reduced motion and on coarse pointers,
 * where a tilt effect is either unwanted or unreachable.
 */
export function usePointerTilt<T extends HTMLElement>() {
  const ref = useRef<T | null>(null);

  useEffect(() => {
    const node = ref.current;
    if (!node || prefersReducedMotion()) {
      return;
    }
    if (window.matchMedia("(pointer: coarse)").matches) {
      return;
    }

    let frame: number | null = null;
    let pending: { x: number; y: number } | null = null;

    const apply = () => {
      frame = null;
      if (!pending) {
        return;
      }
      node.style.setProperty("--lp-mx", pending.x.toFixed(3));
      node.style.setProperty("--lp-my", pending.y.toFixed(3));
    };

    const onMove = (event: PointerEvent) => {
      const box = node.getBoundingClientRect();
      pending = {
        x: ((event.clientX - box.left) / box.width) * 2 - 1,
        y: ((event.clientY - box.top) / box.height) * 2 - 1,
      };
      frame ??= requestAnimationFrame(apply);
    };

    const onLeave = () => {
      pending = { x: 0, y: 0 };
      frame ??= requestAnimationFrame(apply);
    };

    node.addEventListener("pointermove", onMove);
    node.addEventListener("pointerleave", onLeave);
    return () => {
      node.removeEventListener("pointermove", onMove);
      node.removeEventListener("pointerleave", onLeave);
      if (frame !== null) {
        cancelAnimationFrame(frame);
      }
    };
  }, []);

  return ref;
}
