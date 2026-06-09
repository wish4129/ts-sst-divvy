CREATE TABLE "bursa_universe" (
	"code" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"market" text NOT NULL,
	"sector" text,
	"in_watchlist" boolean DEFAULT false NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "score_composite" integer DEFAULT 50;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "score_subs" jsonb DEFAULT '{}';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "financials" jsonb DEFAULT '[]';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "dividends" jsonb DEFAULT '[]';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "last_price" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "price_change" numeric DEFAULT '0';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "dividend_yield" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "pe_ratio" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "roe" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "debt_to_equity" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "market_cap" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "sparkline" jsonb DEFAULT '[]';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "notes" text DEFAULT '';--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "revisit_at" timestamp with time zone;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "target_price" numeric;--> statement-breakpoint
ALTER TABLE "stocks" ADD COLUMN "cut_loss_price" numeric;