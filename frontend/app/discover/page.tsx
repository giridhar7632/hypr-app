"use client"

import { Stock, usePopularQuotes } from "@/hooks/usePopularQuotes";
import { fetchData, slideInOut } from "@/lib/utils";
import { useQuery } from "@tanstack/react-query";
import { ArrowUpRight } from "lucide-react";
import { useTransitionRouter } from "next-view-transitions";

import {SimpleTextReveal} from "@/components/SimpleTextReveal";
import ReactLenis from "lenis/react";

function Card({ ticker, change_amount, change_percentage, price, delay }: Stock & { delay?: boolean }) {
  return (
    <div className="flex text-[6vw] justify-between gap-4 py-4 md:py-12 border-b border-[#eee] w-full h-[10vh] items-center">
      <SimpleTextReveal
        start={"top 95%"}
        delay={delay ? 0.5 : 0}
        className="font-bold tracking-tight leading-tight whitespace-nowrap w-[30%] md:w-[30%] text-left pl-2 overflow-hidden"
      >
        <p>{ticker}</p>
      </SimpleTextReveal>

      <SimpleTextReveal
        start={"top 95%"}
        delay={delay ? 0.7 : 0}
        className="font-semibold flex items-baseline w-[30%]"
      >
        <p>
          <span className="text-[2vw] font-normal">$</span>
          {parseFloat(price).toFixed(2)}
          <span
            className={`text-[2vw] font-normal ${
              parseFloat(change_amount) > 0 ? "text-green-500" : "text-red-500"
            }`}
          >
            {parseFloat(change_amount) > 0 ? "+" : ""}
            {parseFloat(change_amount).toFixed(2)}
          </span>
        </p>
      </SimpleTextReveal>

      <SimpleTextReveal
        start={"top 95%"}
        delay={delay ? 0.7 : 0}
        className={`font-semibold flex items-baseline w-[20%] ${
          parseFloat(change_percentage) > 0 ? "text-green-500" : "text-red-500"
        }`}
      >
        <p>
          {parseFloat(change_percentage) > 0 ? "+" : ""}
          {parseFloat(change_percentage).toFixed(2)}
          <span className="text-[2vw] font-normal">%</span>
        </p>
      </SimpleTextReveal>

      <SimpleTextReveal
        start={"top 95%"}
        delay={delay ? 0.7 : 0}
        className="w-[10vh] h-[10vh] flex items-center justify-center"
      >
        <ArrowUpRight className="w-[10vh] h-[10vh] flex items-center justify-center" />
      </SimpleTextReveal>
    </div>
  );
}


function SkeletonCard() {
  return (
      <div className="flex text-[6vw] h-[12vh] justify-between gap-4 py-4 md:py-12 border-b border-[#eee] w-full h-[10vh] items-center px-2">
          <div className="w-[30%] overflow-hidden h-[16px] bg-gray-200 animate-pulse"></div>
          <div className="w-[30%] h-[16px] bg-gray-200 animate-pulse"></div>
          <div className="w-[20%] h-[16px] bg-gray-200 animate-pulse"></div>
          <div className="w-[10vh] h-[10vh] flex items-center justify-center">
          <div className="w-[10vh] h-[10vh] flex items-center justify-center bg-gray-200 animate-pulse"></div>
          </div>
      </div>
  )
}

export default function Discover() {

  const { data: stocks, isLoading } = usePopularQuotes();
  const {data: trending, isLoading: isTrendingLoading} = useQuery({
    queryKey: ['trending-stocks'],
    queryFn: () => fetchData(`${process.env.NEXT_PUBLIC_BACKEND_URL || ''}/trending`),
    enabled: !isLoading,
    refetchOnWindowFocus: true
  });
    const router = useTransitionRouter()
    return (
      <ReactLenis root>
        <div className="discover flex flex-col items-center text-center justify-center w-screen min-h-screen my-16 py-8">
            <SimpleTextReveal delay={0.5} className="text-[6vw] font-bold tracking-tight leading-tight whitespace-nowrap"><h1>Discover</h1></SimpleTextReveal>
            <SimpleTextReveal delay={0.8} className="text-[3vw] md:text-2xl"><p>Discover the popular and trending stocks.</p></SimpleTextReveal>
            <h2 className="text-[4vw] font-bold tracking-tight leading-tight whitespace-nowrap mt-16">Most Popular</h2>
            <ol className="flex flex-col w-screen gap-8 items-center justify-center mt-16">
                {isLoading ? Array.from({ length: 4 }).map((_, index) => (
                    <SkeletonCard key={index} />
                )) : stocks?.map((item, index) => (
                    <li key={index} className="w-full"><a onClick={(e) => {
                                    e.preventDefault()
                                    router.push(`/company/${item.ticker}`, {
                                        onTransitionReady: slideInOut
                                    })
                                }} href={`/company/${item.ticker}`}><Card {...item} delay={index > 2 ? false : true} /></a></li>
                ))} 
            </ol>
            <h2 className="text-[4vw] font-bold tracking-tight leading-tight whitespace-nowrap mt-16">Top Gainers</h2>
            <ol className="flex flex-col w-screen gap-8 items-center justify-center mt-16">
                {isTrendingLoading ? Array.from({ length: 4 }).map((_, index) => (
                    <SkeletonCard key={index} />
                )) : trending?.top_gainers?.map((item: any, index: number) => (
                    <li key={index} className="w-full"><a onClick={(e) => {
                                    e.preventDefault()
                                    router.push(`/company/${item.ticker}`, {
                                        onTransitionReady: slideInOut
                                    })
                                }} href={`/company/${item.ticker}`}><Card {...item} delay={false} /></a></li>
                ))} 
            </ol>
            <h2 className="text-[4vw] font-bold tracking-tight leading-tight whitespace-nowrap mt-16">Top Losers</h2>
            <ol className="flex flex-col w-screen gap-8 items-center justify-center mt-16">
                {isTrendingLoading ? Array.from({ length: 4 }).map((_, index) => (
                    <SkeletonCard key={index} />
                )) : trending?.top_losers?.map((item: any, index: number) => (
                    <li key={index} className="w-full"><a onClick={(e) => {
                                    e.preventDefault()
                                    router.push(`/company/${item.ticker}`, {
                                        onTransitionReady: slideInOut
                                    })
                                }} href={`/company/${item.ticker}`}><Card {...item} delay={false} /></a></li>
                ))} 
            </ol>
            <h2 className="text-[4vw] font-bold tracking-tight leading-tight whitespace-nowrap mt-16">Most Activly Traded</h2>
            <ol className="flex flex-col w-screen gap-8 items-center justify-center mt-16">
                {isTrendingLoading ? Array.from({ length: 4 }).map((_, index) => (
                    <SkeletonCard key={index} />
                )) : trending?.most_actively_traded?.map((item: any, index: number) => (
                    <li key={index} className="w-full"><a onClick={(e) => {
                                    e.preventDefault()
                                    router.push(`/company/${item.ticker}`, {
                                        onTransitionReady: slideInOut
                                    })
                                }} href={`/company/${item.ticker}`}><Card {...item} delay={false} /></a></li>
                ))} 
            </ol>

        </div>
        </ReactLenis>
    );
}