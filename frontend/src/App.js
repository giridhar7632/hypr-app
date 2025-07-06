import React, { useState, useEffect, useRef } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';
import { TrendingUp, TrendingDown, Minus, Wifi, WifiOff, AlertCircle, Activity } from 'lucide-react';

const MarketSentimentDashboard = () => {
  const [sentimentData, setSentimentData] = useState({});
  const [newsData, setNewsData] = useState([]);
  const [historicalData, setHistoricalData] = useState({});
  const [connected, setConnected] = useState(false);
  const [lastUpdate, setLastUpdate] = useState(null);
  const [selectedSymbol, setSelectedSymbol] = useState('AAPL');
  const [demoMode, setDemoMode] = useState(false);
  const [hasReceivedRealData, setHasReceivedRealData] = useState(false);
  const ws = useRef(null);
  const intervalRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);

  // Mock data generators with more realistic values
  const generateMockSentiment = () => {
    // Generate more varied sentiment values
    const sentiment = (Math.random() - 0.5) * 1.6; // Range: -0.8 to 0.8
    const confidence = Math.random() * 0.3 + 0.7; // Range: 0.7 to 1.0
    let signal = 'HOLD';
    
    if (sentiment > 0.3) signal = 'BUY';
    else if (sentiment < -0.3) signal = 'SELL';

    return {
      sentiment: parseFloat(sentiment.toFixed(3)),
      confidence: parseFloat(confidence.toFixed(3)),
      signal,
      timestamp: new Date().toISOString()
    };
  };

  const generateMockNews = () => {
    const headlines = [
      "Tech Giants Report Strong Q4 Earnings Beating Expectations",
      "Federal Reserve Signals Potential Interest Rate Changes",
      "AI Sector Shows Unprecedented Growth in Market Valuation",
      "Market Volatility Decreases Following Positive Policy Changes",
      "Energy Stocks Surge on Supply Chain Improvements",
      "Healthcare Innovation Drives Strong Sector Performance",
      "Cryptocurrency Market Shows Signs of Long-term Stabilization",
      "Retail Earnings Beat Analyst Expectations Across Board"
    ];

    const sources = ["Reuters", "Bloomberg", "CNBC", "Wall Street Journal", "MarketWatch"];
    const symbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA'];

    return Array.from({ length: 5 }, (_, i) => ({
      title: headlines[Math.floor(Math.random() * headlines.length)],
      summary: "Market analysis reveals significant developments in key sectors with potential implications for investors and market dynamics moving forward. Expert analysts provide insights into emerging trends.",
      published: new Date(Date.now() - Math.random() * 86400000).toISOString(),
      source: sources[Math.floor(Math.random() * sources.length)],
      sentiment_score: parseFloat(((Math.random() - 0.5) * 1.5).toFixed(3)),
      sentiment_label: Math.random() > 0.5 ? 'positive' : Math.random() > 0.5 ? 'negative' : 'neutral',
      symbols: symbols.slice(0, Math.floor(Math.random() * 3) + 1)
    }));
  };

  const initializeMockData = () => {
    const trackedSymbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ'];
    const mockSentiment = {};
    const mockHistorical = {};

    trackedSymbols.forEach(symbol => {
      mockSentiment[symbol] = generateMockSentiment();
      
      // Generate historical data (last 20 points)
      mockHistorical[symbol] = Array.from({ length: 20 }, (_, i) => {
        const time = new Date(Date.now() - (19 - i) * 60000);
        const sentiment = (Math.random() - 0.5) * 1.4;
        const confidence = Math.random() * 0.3 + 0.7;
        let signal = 'HOLD';
        
        if (sentiment > 0.3) signal = 'BUY';
        else if (sentiment < -0.3) signal = 'SELL';

        return {
          time: time.toLocaleTimeString(),
          sentiment: parseFloat(sentiment.toFixed(3)),
          signal,
          confidence: parseFloat(confidence.toFixed(3))
        };
      });
    });

    setSentimentData(mockSentiment);
    setHistoricalData(mockHistorical);
    setNewsData(generateMockNews());
    setLastUpdate(new Date().toLocaleTimeString());
  };

  const updateMockData = () => {
    // Only update mock data if we're in demo mode and haven't received real data recently
    if (!demoMode || hasReceivedRealData) return;
    
    const trackedSymbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ'];
    
    // Update sentiment data
    setSentimentData(prev => {
      const updated = { ...prev };
      trackedSymbols.forEach(symbol => {
        updated[symbol] = generateMockSentiment();
      });
      return updated;
    });

    // Update historical data
    setHistoricalData(prev => {
      const updated = { ...prev };
      trackedSymbols.forEach(symbol => {
        const newPoint = {
          time: new Date().toLocaleTimeString(),
          sentiment: parseFloat(((Math.random() - 0.5) * 1.4).toFixed(3)),
          signal: ['BUY', 'SELL', 'HOLD'][Math.floor(Math.random() * 3)],
          confidence: parseFloat((Math.random() * 0.3 + 0.7).toFixed(3))
        };
        
        updated[symbol] = [...(prev[symbol] || []).slice(-19), newPoint];
      });
      return updated;
    });

    // Occasionally update news
    if (Math.random() < 0.2) {
      setNewsData(generateMockNews());
    }

    setLastUpdate(new Date().toLocaleTimeString());
  };

  const startDemoMode = () => {
    console.log('Starting demo mode');
    setDemoMode(true);
    setHasReceivedRealData(false);
    
    if (!intervalRef.current) {
      initializeMockData();
      intervalRef.current = setInterval(updateMockData, 10000); // Every 10 seconds
    }
  };

  const stopDemoMode = () => {
    console.log('Stopping demo mode');
    setDemoMode(false);
    
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }
  };

  const connectWebSocket = () => {
    // Clear any existing reconnect timeout
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }

    try {
      ws.current = new WebSocket('ws://localhost:8000/ws');
      
      ws.current.onopen = () => {
        console.log('WebSocket Connected');
        setConnected(true);
        setHasReceivedRealData(false);
        stopDemoMode();
      };

      ws.current.onmessage = (event) => {
        const message = JSON.parse(event.data);
        console.log('Received WebSocket message:', message.type);
        
        setHasReceivedRealData(true);
        
        switch (message.type) {
          case 'initial_data':
            if (message.sentiment) {
              setSentimentData(message.sentiment);
            }
            if (message.news) {
              setNewsData(message.news);
            }
            setLastUpdate(new Date().toLocaleTimeString());
            break;
            
          case 'sentiment_update':
            const newSentiment = {};
            message.data.forEach(item => {
              newSentiment[item.symbol] = item;
              
              setHistoricalData(prev => ({
                ...prev,
                [item.symbol]: [
                  ...(prev[item.symbol] || []).slice(-49),
                  {
                    time: new Date(item.timestamp).toLocaleTimeString(),
                    sentiment: item.sentiment,
                    signal: item.signal,
                    confidence: item.confidence
                  }
                ]
              }));
            });
            
            setSentimentData(prev => ({ ...prev, ...newSentiment }));
            setLastUpdate(new Date().toLocaleTimeString());
            break;
            
          case 'news_update':
            // console.log('Received news update:', message.data);
            if (message.data) {
              setNewsData(message.data);
            }
            break;
        }
      };

      ws.current.onclose = (event) => {
        console.log('WebSocket Disconnected:', event.code, event.reason);
        setConnected(false);
        
        // Only start demo mode if we haven't received real data recently
        if (!hasReceivedRealData) {
          startDemoMode();
        }
        
        // Try to reconnect after 5 seconds
        reconnectTimeoutRef.current = setTimeout(() => {
          console.log('Attempting to reconnect...');
          connectWebSocket();
        }, 5000);
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket Error:', error);
        setConnected(false);
        
        if (!hasReceivedRealData) {
          startDemoMode();
        }
      };
    } catch (error) {
      console.error('Failed to create WebSocket:', error);
      setConnected(false);
      startDemoMode();
    }
  };

  useEffect(() => {
    // Try to connect to WebSocket first
    connectWebSocket();
    
    // Start with demo mode after a short delay if no connection
    const demoTimeout = setTimeout(() => {
      if (!connected && !hasReceivedRealData) {
        startDemoMode();
      }
    }, 2000);

    return () => {
      if (ws.current) {
        ws.current.close();
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      clearTimeout(demoTimeout);
    };
  }, []);

  const getSentimentIcon = (sentiment, signal) => {
    if (signal === 'BUY') return <TrendingUp style={{ width: '16px', height: '16px', color: '#10B981' }} />;
    if (signal === 'SELL') return <TrendingDown style={{ width: '16px', height: '16px', color: '#EF4444' }} />;
    return <Minus style={{ width: '16px', height: '16px', color: '#6B7280' }} />;
  };

  const getSentimentColor = (sentiment) => {
    if (sentiment > 0.1) return '#059669';
    if (sentiment < -0.1) return '#DC2626';
    return '#4B5563';
  };

  const getSignalStyles = (signal) => {
    switch (signal) {
      case 'BUY': return { backgroundColor: '#10B981', color: 'white' };
      case 'SELL': return { backgroundColor: '#EF4444', color: 'white' };
      default: return { backgroundColor: '#6B7280', color: 'white' };
    }
  };

  const formatSentimentValue = (value) => {
    return value > 0 ? `+${value.toFixed(3)}` : value.toFixed(3);
  };

  const trackedSymbols = ['AAPL', 'GOOGL', 'MSFT', 'TSLA', 'AMZN', 'META', 'NVDA', 'SPY', 'QQQ'];
  const currentHistoricalData = historicalData[selectedSymbol] || [];

  const styles = {
    container: {
      minHeight: '100vh',
      background: 'linear-gradient(135deg, #0F172A 0%, #1E293B 100%)',
      color: 'white',
      padding: '24px',
      fontFamily: 'system-ui, -apple-system, sans-serif'
    },
    maxWidth: {
      maxWidth: '1280px',
      margin: '0 auto'
    },
    header: {
      marginBottom: '32px'
    },
    headerTop: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      flexWrap: 'wrap',
      gap: '16px'
    },
    title: {
      fontSize: '2.25rem',
      fontWeight: 'bold',
      background: 'linear-gradient(to right, #60A5FA, #A855F7)',
      WebkitBackgroundClip: 'text',
      WebkitTextFillColor: 'transparent',
      margin: 0
    },
    subtitle: {
      color: '#9CA3AF',
      marginTop: '8px',
      margin: 0
    },
    demoTag: {
      marginLeft: '8px',
      padding: '4px 8px',
      backgroundColor: '#D97706',
      color: '#FEF3C7',
      fontSize: '0.75rem',
      borderRadius: '4px'
    },
    statusContainer: {
      display: 'flex',
      alignItems: 'center',
      gap: '16px'
    },
    connectionStatus: {
      display: 'flex',
      alignItems: 'center',
      gap: '8px'
    },
    connectedText: {
      fontSize: '0.875rem',
      color: '#10B981'
    },
    disconnectedText: {
      fontSize: '0.875rem',
      color: '#EF4444'
    },
    lastUpdate: {
      fontSize: '0.875rem',
      color: '#9CA3AF'
    },
    grid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
      gap: '16px',
      marginBottom: '32px'
    },
    symbolCard: {
      backgroundColor: '#1E293B',
      borderRadius: '8px',
      padding: '16px',
      border: '2px solid #374151',
      transition: 'all 0.2s ease',
      cursor: 'pointer'
    },
    symbolCardSelected: {
      borderColor: '#3B82F6',
      backgroundColor: '#334155'
    },
    symbolCardHover: {
      borderColor: '#4B5563',
      transform: 'scale(1.02)'
    },
    symbolHeader: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      marginBottom: '8px'
    },
    symbolName: {
      fontWeight: '600',
      fontSize: '1.125rem',
      margin: 0
    },
    sentimentValue: {
      fontSize: '1.5rem',
      fontWeight: 'bold',
      marginBottom: '4px'
    },
    symbolFooter: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between'
    },
    signalBadge: {
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '0.75rem',
      fontWeight: '500'
    },
    confidence: {
      fontSize: '0.75rem',
      color: '#9CA3AF'
    },
    loading: {
      color: '#6B7280'
    },
    loadingBar: {
      height: '32px',
      backgroundColor: '#374151',
      borderRadius: '4px',
      marginBottom: '8px',
      animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
    },
    loadingSmall: {
      height: '16px',
      backgroundColor: '#374151',
      borderRadius: '4px',
      animation: 'pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite'
    },
    chartsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
      gap: '24px',
      marginBottom: '32px'
    },
    chartCard: {
      backgroundColor: '#1E293B',
      borderRadius: '8px',
      padding: '24px',
      border: '1px solid #374151'
    },
    chartTitle: {
      fontSize: '1.25rem',
      fontWeight: '600',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'center',
      margin: 0
    },
    chartIcon: {
      width: '20px',
      height: '20px',
      marginRight: '8px',
      color: '#60A5FA'
    },
    newsCard: {
      backgroundColor: '#1E293B',
      borderRadius: '8px',
      padding: '24px',
      border: '1px solid #374151'
    },
    newsTitle: {
      fontSize: '1.25rem',
      fontWeight: '600',
      marginBottom: '16px',
      display: 'flex',
      alignItems: 'center',
      margin: 0
    },
    newsIcon: {
      width: '20px',
      height: '20px',
      marginRight: '8px',
      color: '#FBBF24'
    },
    newsContent: {
      maxHeight: '384px',
      overflowY: 'auto'
    },
    newsItem: {
      backgroundColor: '#374151',
      borderRadius: '8px',
      padding: '16px',
      border: '1px solid #4B5563',
      marginBottom: '16px'
    },
    newsItemHeader: {
      display: 'flex',
      alignItems: 'flex-start',
      justifyContent: 'space-between',
      marginBottom: '8px'
    },
    newsItemTitle: {
      fontWeight: '500',
      fontSize: '1.125rem',
      color: 'white',
      margin: 0,
      flex: 1
    },
    newsItemSentiment: {
      padding: '4px 8px',
      borderRadius: '4px',
      fontSize: '0.75rem',
      fontWeight: '500',
      marginLeft: '16px',
      backgroundColor: 'rgba(255, 255, 255, 0.1)'
    },
    newsItemSummary: {
      color: '#D1D5DB',
      fontSize: '0.875rem',
      marginBottom: '12px',
      lineHeight: '1.4'
    },
    newsItemFooter: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      fontSize: '0.75rem',
      color: '#9CA3AF'
    },
    newsItemMeta: {
      display: 'flex',
      alignItems: 'center',
      gap: '16px'
    },
    symbolTags: {
      display: 'flex',
      gap: '4px',
      alignItems: 'center'
    },
    symbolTag: {
      backgroundColor: '#2563EB',
      color: 'white',
      padding: '2px 8px',
      borderRadius: '4px'
    },
    symbolExtra: {
      color: '#6B7280'
    },
    emptyState: {
      textAlign: 'center',
      color: '#9CA3AF',
      padding: '32px'
    },
    emptyIcon: {
      width: '48px',
      height: '48px',
      margin: '0 auto 16px',
      opacity: 0.5
    }
  };

  return (
    <div style={styles.container}>
      <style>
        {`
          @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
          }
        `}
      </style>
      <div style={styles.maxWidth}>
        {/* Header */}
        <div style={styles.header}>
          <div style={styles.headerTop}>
            <div>
              <h1 style={styles.title}>
                Market Sentiment Dashboard
              </h1>
              <p style={styles.subtitle}>
                Real-time sentiment analysis from financial news
                {demoMode && (
                  <span style={styles.demoTag}>
                    DEMO MODE
                  </span>
                )}
              </p>
            </div>
            
            <div style={styles.statusContainer}>
              <div style={styles.connectionStatus}>
                {connected ? (
                  <Wifi style={{ width: '20px', height: '20px', color: '#10B981' }} />
                ) : (
                  <WifiOff style={{ width: '20px', height: '20px', color: '#EF4444' }} />
                )}
                <span style={connected ? styles.connectedText : styles.disconnectedText}>
                  {connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              
              {lastUpdate && (
                <div style={styles.lastUpdate}>
                  Last update: {lastUpdate}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Sentiment Overview Grid */}
        <div style={styles.grid}>
          {trackedSymbols.map(symbol => {
            const data = sentimentData[symbol];
            const isSelected = selectedSymbol === symbol;
            
            return (
              <div
                key={symbol}
                style={{
                  ...styles.symbolCard,
                  ...(isSelected ? styles.symbolCardSelected : {})
                }}
                onClick={() => setSelectedSymbol(symbol)}
                onMouseEnter={(e) => {
                  if (!isSelected) {
                    e.target.style.borderColor = '#4B5563';
                    e.target.style.transform = 'scale(1.02)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isSelected) {
                    e.target.style.borderColor = '#374151';
                    e.target.style.transform = 'scale(1)';
                  }
                }}
              >
                <div style={styles.symbolHeader}>
                  <h3 style={styles.symbolName}>{symbol}</h3>
                  {data && getSentimentIcon(data.sentiment, data.signal)}
                </div>
                
                {data ? (
                  <>
                    <div style={{
                      ...styles.sentimentValue,
                      color: getSentimentColor(data.sentiment)
                    }}>
                      {formatSentimentValue(data.sentiment)}
                    </div>
                    <div style={styles.symbolFooter}>
                      <span style={{
                        ...styles.signalBadge,
                        ...getSignalStyles(data.signal)
                      }}>
                        {data.signal}
                      </span>
                      <span style={styles.confidence}>
                        {Math.round(data.confidence * 100)}%
                      </span>
                    </div>
                  </>
                ) : (
                  <div style={styles.loading}>
                    <div style={styles.loadingBar}></div>
                    <div style={styles.loadingSmall}></div>
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {/* Charts Section */}
        <div style={styles.chartsGrid}>
          {/* Historical Sentiment Chart */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>
              <Activity style={styles.chartIcon} />
              Sentiment History - {selectedSymbol}
            </h3>
            
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={currentHistoricalData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="time" 
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  domain={[-1, 1]}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151', 
                    borderRadius: '8px',
                    color: '#F9FAFB'
                  }}
                  formatter={(value, name) => [value.toFixed(3), name]}
                />
                <Legend />
                <Line 
                  type="monotone" 
                  dataKey="sentiment" 
                  stroke="#3B82F6" 
                  strokeWidth={2}
                  dot={{ fill: '#3B82F6', strokeWidth: 2, r: 3 }}
                  name="Sentiment Score"
                />
              </LineChart>
            </ResponsiveContainer>
          </div>

          {/* Confidence Chart */}
          <div style={styles.chartCard}>
            <h3 style={styles.chartTitle}>Confidence Levels</h3>
            
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={trackedSymbols.map(symbol => ({
                symbol,
                confidence: sentimentData[symbol]?.confidence || 0,
                sentiment: sentimentData[symbol]?.sentiment || 0
              }))}>
                <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                <XAxis 
                  dataKey="symbol" 
                  stroke="#9CA3AF"
                  tick={{ fontSize: 12 }}
                />
                <YAxis 
                  stroke="#9CA3AF"
                  domain={[0, 1]}
                  tick={{ fontSize: 12 }}
                />
                <Tooltip 
                  contentStyle={{ 
                    backgroundColor: '#1F2937', 
                    border: '1px solid #374151', 
                    borderRadius: '8px',
                    color: '#F9FAFB'
                  }}
                  formatter={(value, name) => [
                    name === 'confidence' ? `${(value * 100).toFixed(1)}%` : value.toFixed(3), 
                    name === 'confidence' ? 'Confidence' : 'Sentiment'
                  ]}
                />
                <Bar dataKey="confidence" fill="#10B981" name="Confidence" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Recent News */}
        <div style={styles.newsCard}>
          <h3 style={styles.newsTitle}>
            <AlertCircle style={styles.newsIcon} />
            Recent Market News
          </h3>
          {newsData.length > 0 ? (
            <div style={styles.newsContent}>
              {newsData.filter(news => news.symbols.includes(selectedSymbol)).map((news, index) => (
                <div key={index} style={styles.newsItem}>
                  <div style={styles.newsItemHeader}>
                    <h4 style={styles.newsItemTitle}>{news.title}</h4>
                    <div style={styles.newsItemSentiment}>
                      <span style={{ color: getSentimentColor(news.sentiment_score) }}>
                        {formatSentimentValue(news.sentiment_score)}
                      </span>
                    </div>
                  </div>
                  
                  <p style={styles.newsItemSummary}>{news.summary}</p>
                  
                  <div style={styles.newsItemFooter}>
                    <div style={styles.newsItemMeta}>
                      <span>{news.source}</span>
                      {news.symbols && news.symbols.length > 0 && (
                        <div style={styles.symbolTags}>
                          {news.symbols.slice(0, 3).map(symbol => (
                            <span key={symbol} style={styles.symbolTag}>
                              {symbol}
                            </span>
                          ))}
                          {news.symbols.length > 3 && (
                            <span style={styles.symbolExtra}>+{news.symbols.length - 3}</span>
                          )}
                        </div>
                      )}
                    </div>
                    <span>{new Date(news.published).toLocaleString()}</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div style={styles.emptyState}>
              <AlertCircle style={styles.emptyIcon} />
              <p>No recent news available. Waiting for updates...</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default MarketSentimentDashboard;