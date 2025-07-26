CREATE TABLE users (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL DEFAULT '',
    avatar_url TEXT,
    bio TEXT,
    role VARCHAR(50) DEFAULT 'user',
    is_verified BOOLEAN DEFAULT false,
    system_info JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE tokens (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    type VARCHAR(50) DEFAULT 'magic',
    used BOOLEAN DEFAULT false,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE trending_stocks (
  id SERIAL PRIMARY KEY,
  top_gainers JSONB,
  top_losers JSONB,
  most_actively_traded JSONB,
  last_updated TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE live_quotes (
    ticker TEXT PRIMARY KEY,
    price NUMERIC,
    change_amount NUMERIC,
    change_percentage NUMERIC,
    updated_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE data (
  
  ticker TEXT PRIMARY KEY NOT NULL,
  last_run TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

  company_info JSONB,
  financial_data JSONB,
  news_data JSONB,
  social_data JSONB,
  expanded_data JSONB,
  scores JSONB,

  UNIQUE(ticker, last_run)
);

CREATE TABLE company_info (
  ticker VARCHAR(10) PRIMARY KEY,       -- e.g., AAPL, GOOGL
  name TEXT NOT NULL,
  country TEXT NOT NULL,
  currency VARCHAR(10) NOT NULL,
  estimate_currency VARCHAR(10),        -- Optional
  exchange TEXT NOT NULL,
  finnhub_industry TEXT NOT NULL,
  ipo DATE,                              -- Optional, date string like '2012-05-18'
  logo TEXT,                             -- URL, optional
  market_capitalization NUMERIC(20, 2) NOT NULL,
  share_outstanding NUMERIC(20, 2),
  weburl TEXT,
  UNIQUE(ticker)
);

CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_tokens_token ON tokens(token);
CREATE INDEX idx_tokens_user_id ON tokens(user_id);
CREATE INDEX updated_at_idx ON trending_stocks(last_updated);
CREATE INDEX data_ticker_idx ON data (ticker);
CREATE INDEX data_last_run_idx ON data (last_run);
CREATE INDEX company_ticker_idx ON company_info (ticker);