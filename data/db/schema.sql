-- Supabase / PostgreSQL Schema for EarningsEdge

-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- 1. Tickers (Watchlist)
CREATE TABLE tickers (
    symbol VARCHAR(10) PRIMARY KEY,
    company_name VARCHAR(100) NOT NULL,
    next_earnings_date TIMESTAMP WITH TIME ZONE,
    sector VARCHAR(50)
);

-- 2. Scraped Content (The raw data Ilyas fetches)
CREATE TABLE scraped_sources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) REFERENCES tickers(symbol),
    source_type VARCHAR(50) NOT NULL, -- '10-Q', '10-K', 'transcript', 'news', 'hiring'
    url TEXT,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    raw_text TEXT,
    cleaned_json JSONB, -- For LLM-extracted transcript Q&A
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 3. Embeddings (What Mohamed retrieves from)
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id UUID REFERENCES scraped_sources(id),
    ticker VARCHAR(10) REFERENCES tickers(symbol),
    chunk_text TEXT NOT NULL,
    embedding VECTOR(1536), -- Assuming OpenAI text-embedding-3-small
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 4. Briefs (What Mohamed outputs & Adil reads/enriches)
CREATE TABLE briefs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(10) REFERENCES tickers(symbol),
    quarter VARCHAR(20) NOT NULL, -- e.g., 'Q3 2024'
    raw_brief_json JSONB NOT NULL, -- The [D] Data Contract
    enriched_brief_json JSONB,     -- The [E] Data Contract
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX idx_chunks_ticker ON document_chunks(ticker);
CREATE INDEX idx_sources_ticker_date ON scraped_sources(ticker, published_at DESC);