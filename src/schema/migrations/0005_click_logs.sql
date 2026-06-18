-- Add click_logs table for Universe click-through analytics
-- Tracks which stock detail pages users navigate to from search results.
CREATE TABLE IF NOT EXISTS "click_logs" (
  "id" serial PRIMARY KEY,
  "query" text NOT NULL,
  "stock_code" text NOT NULL,
  "position" integer NOT NULL DEFAULT 0,
  "session_id" text,
  "created_at" timestamp with time zone NOT NULL DEFAULT NOW()
);
--> statement-breakpoint
-- Index for top-clicked stocks aggregation
CREATE INDEX IF NOT EXISTS idx_click_logs_stock_code ON "click_logs" ("stock_code");
--> statement-breakpoint
-- Index for time-range queries
CREATE INDEX IF NOT EXISTS idx_click_logs_created_at ON "click_logs" ("created_at");
--> statement-breakpoint
-- Composite index for query-to-click analysis
CREATE INDEX IF NOT EXISTS idx_click_logs_query_created_at ON "click_logs" ("query", "created_at");
