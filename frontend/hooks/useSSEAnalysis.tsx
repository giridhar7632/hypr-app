import { useState } from "react"

export interface AnalysisStep {
    step: string
    status: 'started' | 'success' | 'error'
    message: string
    data?: any
  }
  
 export interface AnalysisData {
    ticker: string
    company_info: {
      name: string
      ticker: string
      country: string
      industry: string
      exchange: string
      marketCap: number
      url: string
    }
    financial_data: {
      ticker: string
      current_price: number
      opening_price: number
      daily_high: number
      daily_low: number
      price_change: number
      trading_volume: number
      volatility: number
      historical_data: Record<string, {
        Open: number
        High: number
        Low: number
        Close: number
        Volume: number
      }>
      description: string
    }
    news_data: {
      articles: Array<{
        title: string
        description: string
        url: string
        published_at: string
        source: string
        sentiment: number
        label: string
        confidence: number
      }>
    }
    scores: {
      financial_momentum: number
      news_sentiment: number
      social_buzz: number
      hype_index: number
      sentiment_price_divergence: number
      trading_signal: string
    }
    social_data: {
      total_posts: number
      avg_sentiment: number
    }
  }
  
export const useSSEAnalysis = (ticker: string) => {
    const [steps, setSteps] = useState<AnalysisStep[]>([])
    const [finalData, setFinalData] = useState<AnalysisData | null>(null)
    const [isCache, setIsCache] = useState(false)
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState<string | null>(null)
  
    const startAnalysis = async (forceRefresh = false) => {
      setSteps([])
      setFinalData(null)
      setIsLoading(true)
      setError(null)
  
      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_BACKEND_URL}/analyze`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ symbol: ticker, force_refresh: forceRefresh }),
        })
  
        if (!response.ok) {
          throw new Error('Failed to start analysis')
        }
  
        const reader = response.body?.getReader()
        const decoder = new TextDecoder()
  
        if (!reader) {
          throw new Error('No response body')
        }
  
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
  
          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')
  
          for (const line of lines) {
            if (line.startsWith('data: ')) {
              // console.log("line", line)
              try {
                const data = JSON.parse(line.slice(6))
                // console.log("line data", data)
                setSteps(prev => {
                  const existing = prev.find(s => s.step === data.step)
                  if (existing) {
                    return prev.map(s => s.step === data.step ? data : s)
                  }
                  return [...prev, data]
                })
                
                if(data.step === 'cache' && data.status === 'warning') {
                  setFinalData(data.data)
                  setIsLoading(false)
                  setIsCache(true)
                }
                else if (data.step === 'complete' && data.status === 'success') {
                  setIsCache(false)
                  setFinalData(data.data)
                  setIsLoading(false)
                  break
                } else if (data.status === 'error') {
                  setError(data.message)
                  setIsLoading(false)
                }
              } catch (e) {
                console.error('Failed to parse SSE data:', e)
              }
            }
          }
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error occurred')
        setIsLoading(false)
      }
    }
  
    return {
      steps,
      finalData,
      isLoading,
      error,
      isCache,
      startAnalysis
    }
  }