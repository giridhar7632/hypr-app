import { useEffect, useRef } from "react";
import gsap from "gsap";
import { usePopularQuotes, Stock } from "@/hooks/usePopularQuotes";
import { useHealthCheck } from "@/hooks/useHealthCheck";

export default function Marquee() {
  const { data: healthCheckData, isLoading: isHealthCheckLoading, isError: isHealthCheckError } = useHealthCheck();
  const turnOnDemoMode = !healthCheckData?.success || isHealthCheckLoading || isHealthCheckError;

  const { data: stocks, isLoading } = usePopularQuotes(turnOnDemoMode);

  const containerRef = useRef<HTMLDivElement>(null);
  const contentRef = useRef<HTMLDivElement>(null);
  const animationRef = useRef<gsap.core.Tween | null>(null);
  const popUpTweenRef = useRef<gsap.core.Tween | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    if (isLoading) {
      gsap.set(containerRef.current, { opacity: 0, y: 400 });
      popUpTweenRef.current?.kill();
    } else {
      popUpTweenRef.current = gsap.to(containerRef.current, {
        opacity: 1,
        y: 0,
        duration: 1,
        ease: "power4.out",
        delay: 0,
      });
    }
  }, [isLoading]);
  useEffect(() => {
    if (!contentRef.current || !containerRef.current) return;

    gsap.set(contentRef.current, { x: 0 });

    if (animationRef.current) {
      animationRef.current.kill();
      animationRef.current = null;
    }

    if (isLoading) return;

    const content = contentRef.current;
    const contentWidth = content.scrollWidth;
    const containerWidth = containerRef.current.offsetWidth;

    if (contentWidth <= containerWidth) return;

    const MARQUEE_SPEED = 100;
    const duration = contentWidth / MARQUEE_SPEED;

    function startMarquee() {
      animationRef.current = gsap.fromTo(
        content,
        { x: 0 },
        {
          x: -contentWidth,
          duration,
          ease: "linear",
          onComplete: () => {
            gsap.set(content, { x: 0 });
            startMarquee();
          },
        }
      );
    }

    startMarquee();

    return () => {
      if (animationRef.current) {
        animationRef.current.kill();
        animationRef.current = null;
      }
    };
  }, [stocks, isLoading]);

  const renderItems = () => {
    if (isLoading) {
      return Array.from({ length: 7 }, (_, i) => (
        <div
          className="marquee__item md:text-4xl text-2xl font-bold opacity-50 px-6"
          key={`loading-${i}`}
        >
          -
        </div>
      ));
    }

    return stocks?.map((item: Stock) => {
      const amt = Number(item.change_amount);
      const pct = Number(item.change_percentage);
      return (
        <div
          className="marquee__item md:text-4xl text-2xl flex items-center justify-center gap-2 border-r-4 border-[#eee]/50 px-4 md:px-8"
          key={item.ticker}
        >
          <span className="font-bold">{item.ticker}</span>
          <span className={`font-semibold ${amt > 0 ? "text-green-500" : "text-red-500"}`}>
            {amt > 0 ? "+" : ""}
            {amt.toFixed(2) || "0.00"}
          </span>
          <span className={`${pct > 0 ? "text-green-500" : "text-red-500"}`}>
            ({pct > 0 ? "+" : ""}
            {pct.toFixed(2) || "0.00"}%)
          </span>
        </div>
      );
    });
  };

  return (
    <div
      ref={containerRef}
      className="marquee overflow-hidden whitespace-nowrap w-full bg-[#111] text-[#eee] py-6 md:py-10"
      style={{ position: "relative" }}
    >
      <div
        ref={contentRef}
        style={{
          display: "inline-flex",
          whiteSpace: "nowrap",
        }}
      >
        {renderItems()}
        {renderItems()}
      </div>
    </div>
  );
}
