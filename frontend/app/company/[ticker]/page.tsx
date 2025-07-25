'use client'
import { use, useState } from 'react'
import {SimpleTextReveal} from '@/components/SimpleTextReveal';
import {
  Label,
  PolarGrid,
  PolarRadiusAxis,
  RadialBar,
  RadialBarChart, CartesianGrid, Line, LineChart, XAxis 
} from "recharts"
import { ChartConfig,
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent } from '@/components/ui/chart';
import { ArrowUpRight, TrendingDown, TrendingUp } from 'lucide-react';

export default function SymbolPage({
  params,
}: {
  params: Promise<{ ticker: string }>
}) {
  const { ticker } = use(params)

  const [data, setData] = useState({
    symbol: 'AAPL',
    changePercent: 1.08,
    value: 150.23,
    sentiment: 'positive',
    company: 'Apple Inc.',
    confidence: 0.9,
    marketCap: 2.5,
    industry: 'Technology',
    website: 'https://www.apple.com',
    exchange: 'NASDAQ',
    combinedHypeIndex: 0.9,
    financialMomentum: 0.6,
    newsSentiment: 0.76,
    socialBuzz: 0.45,
    high: 150.23,
    low: 145.23,
    open: 148.23,
    close: 149.23,
    volume: 1000000,
    sentimentPriceDivergence: -0.2,
    date: '2022-01-01',
    description: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services. Their products include iPhones, iPads, Macs, and Apple Watches which are some of the most popular and innovative products in the world.',
    news: [
      {
        title: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
        date: '2022-01-01',
        source: 'Yahoo Finance',
        sentiment: 'positive',
        url: 'https://finance.yahoo.com/quote/AAPL/news',
        content: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
      },
      {
        title: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
        date: '2022-01-01',
        source: 'Yahoo Finance',
        sentiment: 'negative',
        url: 'https://finance.yahoo.com/quote/AAPL/news',
        content: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
      },
      {
        title: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
        date: '2022-01-01',
        source: 'Yahoo Finance',
        sentiment: 'neutral',
        url: 'https://finance.yahoo.com/quote/AAPL/news',
        content: 'Apple Inc. is a technology company that designs, manufactures, and sells consumer electronics, software, and online services.',
      },
    ]
  })
  const chartData = [
    { browser: "safari", hypeIndex: data.combinedHypeIndex, fill: "#111" },
  ]
  const chartConfig = {
    hypeIndex: {
      label: "Hype Index",
    },
    desktop: {
      label: "Desktop",
      color: "#111",
    },
  } satisfies ChartConfig
  const lineChartData = [
    { month: "January", desktop: 186 },
    { month: "February", desktop: 305 },
    { month: "March", desktop: 237 },
    { month: "April", desktop: 73 },
    { month: "May", desktop: 209 },
    { month: "June", desktop: 214 },
  ]
 
  return (
    <div className="company discover flex flex-col items-center w-screen min-h-screen my-16 py-16">

      <SimpleTextReveal delay={0.5} className="text-3xl md:text-[6vw] font-bold tracking-tight leading-tight text-center"><h1>{data.company}</h1></SimpleTextReveal>

      <div className='flex text-3xl md:text-[6vw] bg-[#111] flex-wrap md:flex-nowrap justify-between md:gap-4 py-4 md:py-2 text-[#eee] w-full h-full items-center px-2'>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal text-[#eee]'>Symbol</p><SimpleTextReveal start={"top 95%"} delay={1.2} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.symbol}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal text-[#eee]'>Value</p><SimpleTextReveal start={"top 95%"} delay={1.2} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.value}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal text-[#eee]'>Change</p><SimpleTextReveal start={"top 95%"} delay={1.2} className={`font-semibold tracking-tight leading-tight whitespace-nowrap ${data.sentiment === 'positive' ? 'text-green-500' : 'text-red-500'}`}><p>{data.sentiment === 'positive' ? '+' : '-'}{data.changePercent}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal text-[#eee]'>Sentiment (confidence)</p><SimpleTextReveal start={"top 95%"} delay={1.2} className={`font-semibold tracking-tight leading-tight whitespace-nowrap ${data.sentiment === 'positive' ? 'text-green-500' : 'text-red-500'}`}><p>{data.sentiment === 'positive' ? 'BUY' : data.sentiment === 'negative' ? 'SELL' : 'HOLD'}<span className="text-[2vw] font-normal text-[#eee]">({data.confidence * 100}%)</span></p></SimpleTextReveal></div>
      </div>

      <div className="w-full flex flex-col md:flex-row px-4 md:px-8 my-8">
        <p className="w-full md:w-[40%]">About the company:</p>
        <SimpleTextReveal start={"top 95%"} delay={1.2} className="tracking-tight leading-tight whitespace-wrap md:w-[60%]"><p>{data.description}</p></SimpleTextReveal>
      </div>

      <div className="w-full flex flex-col gap-4 md:gap-0 md:flex-row px-4 md:px-8 my-8">
        <table className='flex-1 h-full'>
          <tbody>
          <tr className='border-b border-[#eee] py-1'>
            <td>Market Cap</td>
            <td className='text-right md:text-left'>${data.marketCap} Million</td>
          </tr>
          <tr className='border-b border-[#eee] py-1'>
            <td>Industry</td>
            <td className='text-right md:text-left'>{data.industry}</td>
          </tr>
          <tr className='border-b border-[#eee] py-1'>
            <td>Website</td>
            <td className='text-right md:text-left'><a href={data.website} target='_blank' className='flex items-center justify-end md:justify-start'>{data.website}<ArrowUpRight className='w-4 h-4' /></a></td>
          </tr>
          <tr className='py-1'>
            <td>Exchange</td>
            <td className='text-right md:text-left'>{data.exchange}</td>
          </tr>
          </tbody>
        </table>
        <div className='flex-1'>
        <ChartContainer
          config={chartConfig}
          className="mx-auto aspect-square h-[120px]"
        >
          <RadialBarChart
            data={chartData}
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
                          {chartData[0].hypeIndex.toLocaleString()}
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

      <h2 className='border-t border-[#eee] pt-4 text-2xl font-bold w-full my-4 px-8'>Price History</h2>

      <div className='w-full flex flex-col gap-8 md:flex-row px-4 md:px-8 my-8'>
      <div className='flex-1 h-[200px]'>
      <ChartContainer className='h-full w-full' config={chartConfig}>
          <LineChart
            accessibilityLayer
            data={lineChartData}
            margin={{
              left: 12,
              right: 12,
            }}
          >
            <CartesianGrid vertical={false} />
            <XAxis
              dataKey="month"
              tickLine={false}
              axisLine={false}
              tickMargin={4}
              tickFormatter={(value) => value.slice(0, 3)}
            />
            <ChartTooltip
              cursor={false}
              content={<ChartTooltipContent hideLabel />}
            />
            <Line
              dataKey="desktop"
              type="natural"
              stroke="var(--color-desktop)"
              strokeWidth={2}
              dot={false}
            />
          </LineChart>
        </ChartContainer>
        </div>
        <table className='flex-1 h-full'>
          <tbody>
          <tr className='border-b border-[#eee] py-1'>
            <td>Date</td>
            <td className='text-right md:text-left'>{data.date}</td>
          </tr>
          <tr className='border-b border-[#eee] py-1'>
            <td>High</td>
            <td className='text-right md:text-left'>{data.high}</td>
          </tr>
          <tr className='border-b border-[#eee] py-1'>
            <td>Open</td>
            <td className='text-right md:text-left'>{data.open}</td>
          </tr>
          <tr className='border-b border-[#eee] py-1'>
            <td>Close</td>
            <td className='text-right md:text-left'>{data.close}</td>
          </tr>
          <tr className='py-1'>
            <td>Low</td>
            <td className='text-right md:text-left'>{data.low}</td>
          </tr>
          </tbody>
        </table>
      </div>

      <div className='flex text-3xl md:text-[6vw] flex-wrap md:flex-nowrap justify-between md:gap-4 py-4 md:py-2 border-y border-[#eee] w-full h-full items-center px-2'>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal'>Financial Momentum</p><SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.financialMomentum}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal'>News Sentiment</p><SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.newsSentiment}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal'>Social Buzz</p><SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.socialBuzz}</p></SimpleTextReveal></div>
        <div className='w-[50%] md:w-[25%] text-left overflow-hidden flex flex-col'><p className='text-sm font-normal'>Sentiment Price Divergence</p><SimpleTextReveal start={"top 95%"} delay={0} className="font-bold tracking-tight leading-tight whitespace-nowrap"><p>{data.sentimentPriceDivergence}</p></SimpleTextReveal></div>
      </div>

      <div className="w-full flex flex-col gap-4 my-8">
        <h2 className="text-left text-3xl md:text-[4vw] font-bold tracking-tight leading-tight px-4">Recent News</h2>
        <div className="w-full flex flex-col gap-4">
          {data.news.map((news, index) => (
            <a href={news.url} target='_blank' key={index} className="w-full block flex flex-col gap-2 border-b border-[#eee] py-2 px-4">
              
              <h3 className="text-left text-lg md:text-2xl font-bold tracking-tight leading-tight">{news.title}</h3>
              <p className="text-left text-md md:text-lg font-normal tracking-tight leading-tight">{news.content}</p>
              <div className="flex items-center text-xs md:text-sm gap-2"><p className="text-left font-normal tracking-tight leading-tight">{news.source}</p> <p className="text-left font-normal tracking-tight leading-tight">{news.date}</p> <p className={`text-left font-normal tracking-tight leading-tight w-6 h-6  ${news.sentiment === 'positive' ? 'text-green-500' : news.sentiment === 'negative' ? 'text-red-500' : 'text-yellow-500'}`}>{news.sentiment === 'positive' ? <TrendingUp className='w-6 h-6' /> : news.sentiment === 'negative' ? <TrendingDown className='w-6 h-6' /> : <span>neutral</span>}</p></div>
            </a>
          ))}
        </div>
      </div>

    </div>
  )
}