"use client";

import React, { useRef, useEffect } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";

gsap.registerPlugin(ScrollTrigger);

interface SimpleTextRevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  start?: string; // scroll trigger start position, e.g. "top 95%"
}

export function SimpleTextReveal({
  children,
  className,
  delay = 0,
  start = "top 95%",
}: SimpleTextRevealProps) {
  const elRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!elRef.current) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        elRef.current,
        { opacity: 0, y: 40 },
        {
          opacity: 1,
          y: 0,
          duration: 0.6,
          ease: "power3.out",
          delay,
          scrollTrigger: {
            trigger: elRef.current,
            start,
            once: true,
          },
        }
      );
    }, elRef);

    return () => ctx.revert();
  }, [delay, start]);

  return (
    <div ref={elRef} className={className}>
      {children}
    </div>
  );
}
