-- Add search_logs table for Universe search trajectory analytics
-- Tracks what users search for, anonymized (no PII/IP), to inform data enrichment priorities.
CREATE TABLE IF NOT EXISTS "search_logs" (
  "id" serial PRIMARY KEY,
  "query" text NOT NULL,
  "result_count" integer NOT NULL DEFAULT 0,
  "session_id" text,
  "created_at" timestamp with time zone NOT NULL DEFAULT NOW()
);
--> statement-breakpoint
-- Index for top-queries aggregation
CREATE INDEX IF NOT EXISTS idx_search_logs_query ON "search_logs" ("query");
--> statement-breakpoint
-- Index for time-range queries
CREATE INDEX IF NOT EXISTS idx_search_logs_created_at ON "search_logs" ("created_at");
