import { useState, useRef, useLayoutEffect } from "react"
import gsap from "gsap"
import { TrendingUp, TrendingDown } from "lucide-react"

function FeedTabs({ data }: { data: any }) {
  const [activeTab, setActiveTab] = useState<"news" | "social">("news")
  const listRef = useRef<HTMLDivElement>(null)
  const feed = activeTab === "news" ? data.news_data.articles : data.social_data.posts.sort((a: any, b: any) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())

  useLayoutEffect(() => {
    if (listRef.current) {
      gsap.fromTo(
        listRef.current.querySelectorAll(".feed-item"),
        { opacity: 0, y: 32 },
        { opacity: 1, y: 0, stagger: 0.1, duration: 0.7, ease: "expo.out" }
      )
    }
  }, [activeTab, feed])

  return (
    <div className="w-full my-8">
      <div className="flex border-b border-[#eee] mb-4">
        <button
          className={`py-2 border-b-4 w-[50%] px-4 text-left cursor-pointer ${activeTab === "news" ? "border-[#111]" : "border-transparent"}`}
          onClick={() => setActiveTab("news")}
        >
          <h2 className={`font-bold text-xl md:text-[4vw] ${activeTab === "news" ? "text-[#111]" : "text-neutral-600"}`}>
            Recent News
          </h2>
        </button>
        <button
          className={`py-2 border-b-4 w-[50%] px-4 text-left cursor-pointer ${activeTab === "social" ? "border-[#111]" : "border-transparent"} ml-4`}
          onClick={() => setActiveTab("social")}
        >
          <h2 className={`font-bold text-xl md:text-[4vw] ${activeTab === "social" ? "text-[#111]" : "text-neutral-600"}`}>
            Social Feed
          </h2>
        </button>
      </div>

      <div ref={listRef} className="flex flex-col gap-4">
        {activeTab === "news" && feed?.length ? (
          feed.map((news: any, index: number) => (
            <a
              href={news.url}
              target="_blank"
              rel="noopener noreferrer"
              key={index}
              className="feed-item w-full block flex flex-col gap-2 border-b border-[#eee] py-2 px-4"
            >
              <h3 className="text-left text-lg md:text-2xl font-bold tracking-tight leading-tight">{news.title}</h3>
              <p className="text-left text-md md:text-lg font-normal tracking-tight leading-tight">{news.description}</p>
              <div className="flex items-center text-xs md:text-sm gap-2">
                <p className="text-left font-normal tracking-tight leading-tight">{news.source}</p>
                <p className="text-left font-normal tracking-tight leading-tight">
                  {new Date(news.published_at).toLocaleDateString()}
                </p>
                <p className={
                  `text-left font-normal tracking-tight leading-tight ${
                    news.label === 'positive' ? 'text-green-500' 
                    : news.label === 'negative' ? 'text-red-500' 
                    : 'text-yellow-500'}`
                }>
                  {news.label === "positive" ? <TrendingUp className="w-6 h-6"/> 
                  : news.label === "negative" ? <TrendingDown className="w-6 h-6"/>
                  : <span>neutral</span>}
                </p>
              </div>
            </a>
          ))
        ) : activeTab === "social" && feed?.length ? (
          feed.map((post: any, index: number) => (
            <a
              href={post.url}
              target="_blank"
              rel="noopener noreferrer"
              key={index}
              className="feed-item w-full block flex flex-col gap-2 border-b border-[#eee] py-2 px-4"
            >
              <h3 className="text-left text-lg md:text-2xl font-bold tracking-tight leading-tight">{post.title || "Unknown"}</h3>
              <p className="text-left text-md md:text-lg font-normal tracking-tight leading-tight break-words">{post.description.slice(0, 256)}...</p>
              <div className="flex flex-wrap items-center text-xs md:text-sm gap-2">
                <p className="text-left w-full font-normal tracking-tight leading-tight">by {post.username} on {post.platform}</p>
                <p className="text-left font-normal tracking-tight leading-tight">
                  {new Date(post.created_at).toLocaleDateString()}
                </p>
                <p className={
                  `text-left font-normal tracking-tight leading-tight ${
                    post.label === 'positive' ? 'text-green-500'
                    : post.label === 'negative' ? 'text-red-500' 
                    : 'text-yellow-500'}`
                }>
                  {post.label === "positive" ? <TrendingUp className="w-6 h-6"/>
                  : post.label === "negative" ? <TrendingDown className="w-6 h-6"/>
                  : <span>neutral</span>}
                </p>
                <p className="text-left font-normal tracking-tight leading-tight">
                  Engagement: {post.engagement || 0}
                </p>
              </div>
            </a>
          ))
        ) : (
          <p className="text-gray-500">No items available.</p>
        )}
      </div>
    </div>
  )
}

export default FeedTabs
