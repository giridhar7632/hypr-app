'use client'
import gsap from "gsap"
import { slideInOut } from "@/lib/utils"
import { ArrowUpRight, RotateCw } from "lucide-react"
import { useTransitionRouter } from "next-view-transitions"
import { SimpleTextReveal } from "@/components/SimpleTextReveal"
import React, { useState, useEffect, useRef, useCallback, useLayoutEffect } from "react"
import { useHealthCheck } from "@/hooks/useHealthCheck"
import { usePopularQuotes } from "@/hooks/usePopularQuotes"

interface SymbolResult {
  description: string
  displaySymbol: string
  symbol: string
  type: string
}

export default function SymbolSearch() {
  const { data: healthCheckData, isLoading: isHealthCheckLoading, isError: isHealthCheckError } = useHealthCheck();
  const turnOnDemoMode = !healthCheckData?.success || isHealthCheckLoading || isHealthCheckError;
  const {data: popularQuotes, isLoading: isPopularQuotesLoading} = usePopularQuotes(turnOnDemoMode)
  const [query, setQuery] = useState("")
  const [results, setResults] = useState<SymbolResult[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const router = useTransitionRouter()

  const debounceTimer = useRef<NodeJS.Timeout | null>(null)
  const resultsRef = useRef<HTMLUListElement>(null)

  const fetchResults = useCallback(async (searchText: string) => {
    if (!searchText.trim()) {
      setResults([])
      return
    }

    if(turnOnDemoMode) {
      setResults(popularQuotes?.map((item) => ({
        description: item.ticker,
        displaySymbol: item.ticker,
        symbol: item.ticker,
        type: "stock"
      })) || [])

      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const url = `https://finnhub.io/api/v1/search?q=${encodeURIComponent(searchText)}&token=${process.env.NEXT_PUBLIC_FINNHUB_API_KEY}`
      const response = await fetch(url)
      if (!response.ok) throw new Error("Failed to fetch results")
      const data = await response.json()
      setResults(data.result?.slice(0, 7) || [])
    } catch (err) {
        console.error(error)
      setError("Failed to fetch results")
    } finally {
      setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    if (debounceTimer.current) clearTimeout(debounceTimer.current)
    debounceTimer.current = setTimeout(() => {
      fetchResults(query)
    }, 800)

    return () => {
      if (debounceTimer.current) clearTimeout(debounceTimer.current)
    }
  }, [query, fetchResults])

  const handleSelect = useCallback((symbol: string) => {
    setQuery("")
    setResults([])
    router.push(`/company/${symbol}`, {
      onTransitionReady: slideInOut,
    })
  }, [router])

  useLayoutEffect(() => {
    if (!resultsRef.current) return
    const items = resultsRef.current.querySelectorAll('li')
    if (!items.length) return

    gsap.fromTo(items,
      { opacity: 0, y: 32 },
      { opacity: 1, y: 0, stagger: 0.1, duration: 0.7, ease: "expo.out" }
    )
  }, [results])

  const onMouseEnter = (e: React.MouseEvent<HTMLLIElement>) => {
    gsap.to(e.currentTarget, { scale: 1.01, duration: 0.2, ease: "power3.out", boxShadow: "0 4px 10px rgba(0,0,0,0.08)" })
  }

  const onMouseLeave = (e: React.MouseEvent<HTMLLIElement>) => {
    gsap.to(e.currentTarget, { scale: 1, duration: 0.2, ease: "power3.out", boxShadow: "0 0 0 rgba(0,0,0,0)" })
  }

  return (
    <div className="discover flex flex-col items-center text-center w-screen min-h-screen py-16">
      <div className="mb-8 mt-[15vh]">
        <SimpleTextReveal delay={0.5} className="text-[6vw] font-bold tracking-tight whitespace-nowrap"><h1>Search</h1></SimpleTextReveal>
      </div>
      <div className="w-full">
        <div className="relative">
          <input
            className="w-full border-b border-[#eee] py-4 text-center text-2xl outline-none"
            placeholder="Start typing company or symbol"
            value={query}
            onChange={e => setQuery(e.target.value)}
            autoFocus
            aria-label="Search for stock symbol"
          />
          {isLoading && (
            <span className="absolute right-4 top-4 text-blue-400">
              <RotateCw className="w-5 h-5 animate-spin" />
            </span>
          )}
        </div>
        {error && <div className="mt-2 text-red-500 text-sm">{error}</div>}
        {results.length > 0 && (
          <ul ref={resultsRef} className="divide-y mt-4 cursor-pointer">
            {results.map(({symbol, description}) => (
              <li
                key={symbol}
                className="flex items-center gap-4 border-b border-[#eee] px-6 transition-transform will-change-transform"
                tabIndex={0}
                onClick={() => handleSelect(symbol)}
                onKeyDown={e => e.key === "Enter" && handleSelect(symbol)}
                onMouseEnter={onMouseEnter}
                onMouseLeave={onMouseLeave}
              >
                <p className="font-bold text-left text-[4vw] w-[20%]">{symbol}</p>
                <p className="text-neutral-500 text-[4vw] truncate flex-1">{description}</p>
                <p className="w-[20%] flex items-center justify-end"><ArrowUpRight className="h-[10vh] w-[10vh]" /></p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
