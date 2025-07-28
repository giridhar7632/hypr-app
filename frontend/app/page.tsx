"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ReactLenis } from "lenis/react";
import { useRef } from "react";
import { SplitText } from "gsap/SplitText";
import { getQueryClient } from "@/app/get-query-client";
import { HydrationBoundary, dehydrate } from "@tanstack/react-query";
import Marquee from "@/components/Marquee";

gsap.registerPlugin(SplitText);

export default function Home() {
  const queryClient = getQueryClient();

  const containerRef = useRef<HTMLDivElement>(null);

  useGSAP(
    () => {
      if (!containerRef.current) return;

      const heroText = new SplitText(".home h1", { type: "words" });
      gsap.set(heroText.words, { opacity: 0, y: 400 });

      gsap.to(heroText.words, {
        opacity: 1,
        y: 0,
        duration: 0.8,
        ease: "power4.out",
        stagger: 0.075,
        delay: 0,
      });
    },
    { scope: containerRef }
  );

  return (
    <HydrationBoundary state={dehydrate(queryClient)}>
      <ReactLenis root>
        <div
          ref={containerRef}
          className="home flex flex-col items-center text-center justify-end max-w-screen w-full h-screen"
        >
          <h1 className="text-[6vw] font-bold absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 tracking-tight leading-tight whitespace-nowrap">
            Trade the Hype. Beat the Market.
          </h1>
          <Marquee />
        </div>
      </ReactLenis>
    </HydrationBoundary>
  );
}
