"use client";

import { useGSAP } from "@gsap/react";
import gsap from "gsap";
import { ReactLenis } from "lenis/react";
import { useRef } from "react";
import { SplitText } from "gsap/SplitText";
import { getQueryClient } from "@/app/get-query-client";
import { HydrationBoundary, dehydrate } from "@tanstack/react-query";
import { Stock, usePopularQuotes } from "@/hooks/usePopularQuotes";
import { horizontalLoop } from "@/lib/horizontalLoop";
import Marquee from "@/components/Marquee";

gsap.registerPlugin(SplitText);

export default function Home() {
  const queryClient = getQueryClient();
  const { data: stocks, isLoading } = usePopularQuotes();

  const containerRef = useRef<HTMLDivElement>(null);
  const marqueeRef = useRef<HTMLDivElement>(null);
  const loopRef = useRef<ReturnType<typeof horizontalLoop> | null>(null);

  // Hero text & marquee fade-in animation
  useGSAP(
    () => {
      if (!containerRef.current) return;

      const heroText = new SplitText(".home h1", { type: "words" });
      gsap.set(heroText.words, { opacity: 0, y: 400 });

      gsap.to(heroText.words, {
        opacity: 1,
        y: 0,
        duration: 1,
        ease: "power4.out",
        stagger: 0.075,
        delay: 0,
      });
    },
    { scope: containerRef }
  );

  // Horizontal marquee loop animation - useLayoutEffect to sync with DOM updates
  // useLayoutEffect(() => {
  //   // Kill previous animation instance if exists
  //   if (loopRef.current) {
  //     loopRef.current.kill();
  //     loopRef.current = null;
  //   }

  //   if (stocks && stocks.length > 0 && marqueeRef.current) {
  //     // Select the current marquee items from the DOM
  //     const items = gsap.utils.toArray(".marquee__item", marqueeRef.current) as HTMLElement[];

  //     if (items.length > 0) {
  //       loopRef.current = horizontalLoop(items, {
  //         repeat: -1,
  //         paddingRight: 16,
  //         speed: 1,
  //       });
  //     }
  //   }

  //   // Cleanup on unmount or stocks change
  //   return () => {
  //     if (loopRef.current) {
  //       loopRef.current.kill();
  //       loopRef.current = null;
  //     }
  //   };
  // }, [stocks]);

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
