'use client'
import { use, useCallback, useEffect } from 'react'
import { SimpleTextReveal } from '@/components/SimpleTextReveal'
import {
  Label,
  PolarGrid,
  PolarRadiusAxis,
  RadialBar,
  RadialBarChart,
  CartesianGrid,
  Line,
  XAxis,  
  YAxis,
  Bar,
  ComposedChart,
} from "recharts"
import {
  ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent
} from '@/components/ui/chart'
import { ArrowUpRight, Loader2, CheckCircle, XCircle, RefreshCw } from 'lucide-react'
import { AnalysisStep, useSSEAnalysis } from '@/hooks/useSSEAnalysis'
import { formatMillionsToReadable } from '@/lib/utils'
import FeedTabs from '@/components/FeedTabs'


const StepIndicator = ({ step, status, message }: AnalysisStep) => {
  const getIcon = () => {
    switch (status) {
      case 'started':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />
      case 'success':
        return <CheckCircle className="w-5 h-5 text-green-500" />
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />
      default:
        return <div className="w-5 h-5 rounded-full border-2 border-gray-300 animate-pulse" />
    }
  }

  const stepLabels: Record<string, string> = {
    company_info: 'Company Information',
    financial_data: 'Financial Data',
    news: 'News Analysis',
    keywords: 'Keyword Expansion',
    social: 'Social Media Analysis',
    calculate: 'Metrics Calculation',
    complete: 'Analysis Complete'
  }

  return (
    <div className="flex items-center gap-3 py-2">
      {getIcon()}
      <div>
        <p className="font-medium">{stepLabels[step] || step}<span className="text-sm text-neutral-600 pl-1">({message})</span></p>
      </div>
    </div>
  )
}

export default function SymbolPage({ params }: { params: Promise<{ ticker: string }> }) {
  const { ticker } = use(params)
  const { steps, finalData, isLoading, error, startAnalysis, isCache } = useSSEAnalysis(ticker)

  const startAnalysisMemo = useCallback(() => {
    startAnalysis();
  }, [startAnalysis]);
  
  useEffect(() => {
    startAnalysisMemo();
  }, [ticker])

  const chartData = finalData?.financial_data?.historical_data ? 
    Object.entries(finalData.financial_data.historical_data)
      .map(([date, data]) => ({
        date,
        price: data.Close,
        volume: data.Volume,
        open: data.Open,
        high: data.High,
        low: data.Low
      }))
      .sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()) 
    : []

  const hypeChartData = finalData?.scores ? [
    { browser: "safari", hypeIndex: finalData.scores.hype_index, fill: "#111" },
  ] : []

  const chartConfig = {
    hypeIndex: {
      label: "Hype Index",
    },
    price: {
      label: "Price",
      color: "#111",
    },
    volume: {
      label: "Volume",
      color: "#888",
    },
  } satisfies ChartConfig

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen">
        <XCircle className="w-16 h-16 text-red-500 mb-4" />
        <h2 className="text-2xl font-bold mb-2">Analysis Failed</h2>
        <p className="text-neutral-600 mb-4">{error}</p>
        <button 
          onClick={startAnalysisMemo}
          className="px-6 py-3 bg-[#111] text-[#eee] font-semibold rounded-lg border hover:bg-neutral-800 cursor-pointer"
        >
          Retry Analysis
        </button>
      </div>
    )
  }

  if (isLoading || !finalData) {
    return (
      <div className="company discover flex flex-col items-center w-screen min-h-screen my-16 py-16">
        <div className="max-w-2xl w-full px-4">
          <h1 className="text-4xl font-bold text-center mb-8">Analyzing {ticker}</h1>
          
          <div className="text-center">
            {steps.map((step, index) => (
              <StepIndicator key={`${step.step}-${index}`} {...step} />
            ))}
          </div>

          {steps.length === 0 && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-8 h-8 animate-spin" />
              <span className="ml-2">Fetching data...</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const data = finalData

  return (
    <div className="company discover flex flex-col items-center w-screen min-h-screen my-16 py-16">
      <div className={`flex items-center justify-end mb-8 w-full px-8`}>
      {isCache ? <p className="text-sm text-neutral-400 animate-pulse">refreshing cache...</p> : 
      <p className='cursor-pointer p-2 flex items-center gap-2 bg-white/50 backdrop-blur-sm px-4 py-2 hover:bg-black/5 border border-[#eee]/50 rounded-lg'><RefreshCw className="w-4 h-4" onClick={() => startAnalysis(true)} /> refresh</p>
      }
      </div>
        <SimpleTextReveal delay={0.5} className="text-3xl md:text-[6vw] font-bold tracking-tight leading-tight text-center">
          <h1>{data.company_info.name}</h1>
        </SimpleTextReveal>

      <div className='flex text-3xl md:text-[6vw] bg-[#111] flex-wrap md:flex-nowrap justify-between md:gap-4 py-4 md:py-2 text-[#eee] w-full h-full items-center px-2'>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal text-[#eee]'>Symbol</p>
          <SimpleTextReveal start={"top 95%"} delay={1.2} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p>{data.company_info.ticker}</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal text-[#eee]'>Current Price</p>
          <SimpleTextReveal start={"top 95%"} delay={1.2} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p><span className='text-sm md:text-2vw'>$</span>{data.financial_data.current_price.toFixed(2)}</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal text-[#eee]'>Change (%)</p>
          <SimpleTextReveal start={"top 95%"} delay={1.2} className={`font-semibold tracking-tight leading-tight whitespace-nowrap ${data.financial_data.price_change > 0 ? 'text-green-500' : 'text-red-500'}`}>
            <p>{data.financial_data.price_change > 0 ? '+' : ''}{data.financial_data.price_change.toFixed(2)}%</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal text-[#eee]'>Signal</p>
          <SimpleTextReveal start={"top 95%"} delay={1.2} className={`font-semibold tracking-tight leading-tight whitespace-nowrap ${data.scores.trading_signal === 'BUY' ? 'text-green-500' : data.scores.trading_signal === 'SELL' ? 'text-red-500' : 'text-yellow-500'}`}>
            <p>{data.scores.trading_signal}</p>
          </SimpleTextReveal>
        </div>
      </div>

      <div className="w-full flex flex-col md:flex-row px-4 md:px-8 my-8">
        <p className="w-full md:w-[40%]">About the company:</p>
        <SimpleTextReveal start={"top 95%"} delay={1.2} className="tracking-tight leading-tight whitespace-wrap md:w-[60%]">
          <p>{data.financial_data.description.slice(0, 512)}...</p>
        </SimpleTextReveal>
      </div>

      <div className="w-full flex flex-col gap-4 md:gap-0 md:flex-row px-4 md:px-8 my-8">
        <table className='flex-1 h-full'>
          <tbody>
            <tr className='border-b border-[#eee] py-1'>
              <td>Market Cap</td>
              <td className='text-right md:text-left'>${formatMillionsToReadable(data.company_info.marketCap)}</td>
            </tr>
            <tr className='border-b border-[#eee] py-1'>
              <td>Industry</td>
              <td className='text-right md:text-left'>{data.company_info.industry}</td>
            </tr>
            <tr className='border-b border-[#eee] py-1'>
              <td>Website</td>
              <td className='text-right md:text-left'>
                <a href={data.company_info.url} target='_blank' className='flex items-center justify-end md:justify-start'>
                  {data.company_info.url}<ArrowUpRight className='w-4 h-4' />
                </a>
              </td>
            </tr>
            <tr className='py-1'>
              <td>Exchange</td>
              <td className='text-right md:text-left'>{data.company_info.exchange}</td>
            </tr>
          </tbody>
        </table>
        <div className='flex-1'>
          <ChartContainer
            config={chartConfig}
            className="mx-auto aspect-square h-[120px]"
          >
            <RadialBarChart
              data={hypeChartData}
              startAngle={0}
              endAngle={250}
              innerRadius={50}
              outerRadius={80}
            >
              <PolarGrid
                gridType="circle"
                radialLines={false}
                stroke="none"
                className="first:fill-muted last:fill-background"
                polarRadius={[56, 44]}
              />
              <RadialBar dataKey="hypeIndex" background cornerRadius={40} />
              <PolarRadiusAxis tick={false} tickLine={false} axisLine={false}>
                <Label
                  content={({ viewBox }) => {
                    if (viewBox && "cx" in viewBox && "cy" in viewBox) {
                      return (
                        <text
                          x={viewBox.cx}
                          y={viewBox.cy}
                          textAnchor="middle"
                          dominantBaseline="middle"
                        >
                          <tspan
                            x={viewBox.cx}
                            y={viewBox.cy}
                            className="fill-foreground text-4xl font-bold"
                          >
                            {hypeChartData[0]?.hypeIndex?.toFixed(0) || '0'}
                          </tspan>
                          <tspan
                            x={viewBox.cx}
                            y={(viewBox.cy || 0) + 24}
                            className="fill-muted-foreground text-xs"
                          >
                            Hype Index
                          </tspan>
                        </text>
                      )
                    }
                  }}
                />
              </PolarRadiusAxis>
            </RadialBarChart>
          </ChartContainer>
        </div>
      </div>

      <h2 className='border-t border-[#eee] pt-4 text-2xl font-bold w-full my-4 px-8'>Price & Volume History</h2>

      <div className='w-full flex flex-col gap-8 md:flex-row px-4 md:px-8 my-8'>
        <div className='flex-1 h-[400px]'>
          <ChartContainer className='h-full w-full' config={chartConfig}>
            <ComposedChart
              data={chartData}
              margin={{
                left: 12,
                right: 12,
                top: 12,
                bottom: 12,
              }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis
                dataKey="date"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tickFormatter={(value) => {
                  const date = new Date(value)
                  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
                }}
              />
              <YAxis 
                yAxisId="price"
                orientation="left"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tickFormatter={(value) => `$${value.toFixed(0)}`}
              />
              <YAxis 
                yAxisId="volume"
                orientation="right"
                tickLine={false}
                axisLine={false}
                tickMargin={8}
                tickFormatter={(value) => `${(value / 1000000).toFixed(1)}M`}
              />
              <ChartTooltip
                content={<ChartTooltipContent 
                  formatter={(value, name) => {
                    if (name === 'price') return ['Price: ', `$${Number(value).toFixed(2)}`]
                    if (name === 'volume') return ['Volume: ', `${Number(value).toLocaleString()}`]
                    return [value, name]
                  }}
                />}
              />
              <Line
                yAxisId="price"
                dataKey="price"
                type="monotone"
                stroke="#111"
                strokeWidth={2}
                dot={false}
              />
              {/* <Line
                yAxisId="price"
                dataKey="high"
                type="monotone"
                stroke="#001"
                strokeWidth={2}
                dot={false}
              />
              <Line
                yAxisId="price"
                dataKey="low"
                type="monotone"
                stroke="#011"
                strokeWidth={2}
                dot={false}
              /> */}
              <Bar
                yAxisId="volume"
                dataKey="volume"
                fill="#88888840"
                radius={[2, 2, 0, 0]}
              />
            </ComposedChart>
          </ChartContainer>
        </div>
        <table className='flex-1 h-full'>
          <tbody>
            <tr className='border-b border-[#eee] py-1'>
              <td>Current Price</td>
              <td className='text-right md:text-left'>${data.financial_data.current_price.toFixed(2)}</td>
            </tr>
            <tr className='border-b border-[#eee] py-1'>
              <td>Daily High</td>
              <td className='text-right md:text-left'>${data.financial_data.daily_high.toFixed(2)}</td>
            </tr>
            <tr className='border-b border-[#eee] py-1'>
              <td>Daily Low</td>
              <td className='text-right md:text-left'>${data.financial_data.daily_low.toFixed(2)}</td>
            </tr>
            <tr className='border-b border-[#eee] py-1'>
              <td>Opening Price</td>
              <td className='text-right md:text-left'>${data.financial_data.opening_price.toFixed(2)}</td>
            </tr>
            <tr className='py-1'>
              <td>Volume</td>
              <td className='text-right md:text-left'>{data.financial_data.trading_volume.toLocaleString()}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div className='flex text-3xl md:text-[6vw] flex-wrap md:flex-nowrap justify-between md:gap-4 py-4 md:py-2 border-y border-[#eee] w-full h-full items-center px-2'>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal'>Financial Momentum</p>
          <SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p>{data.scores.financial_momentum.toFixed(1)}</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal'>News Sentiment</p>
          <SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p>{data.scores.news_sentiment.toFixed(1)}</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal'>Social Buzz</p>
          <SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p>{data.scores.social_buzz.toFixed(1)}</p>
          </SimpleTextReveal>
        </div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'>
          <p className='text-sm font-normal'>Sentiment Price Divergence</p>
          <SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap">
            <p>{data.scores.sentiment_price_divergence.toFixed(1)}</p>
          </SimpleTextReveal>
        </div>
      </div>

      <FeedTabs data={{ news_data: data.news_data, social_data: data.social_data }} />
    </div>
  )
}
