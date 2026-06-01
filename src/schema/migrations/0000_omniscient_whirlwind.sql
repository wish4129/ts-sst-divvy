CREATE TABLE "kronos_forecasts" (
	"id" serial PRIMARY KEY NOT NULL,
	"stock_id" text NOT NULL,
	"generated_at" timestamp with time zone DEFAULT now() NOT NULL,
	"pred_30d_close" numeric NOT NULL,
	"pred_change_pct" numeric NOT NULL,
	"pred_low" numeric,
	"pred_high" numeric,
	"pred_volatility" numeric
);
--> statement-breakpoint
CREATE TABLE "portfolio_holdings" (
	"portfolio_id" uuid NOT NULL,
	"stock_id" text NOT NULL,
	"shares" integer NOT NULL,
	"avg_cost" numeric NOT NULL,
	"target_pct" numeric NOT NULL
);
--> statement-breakpoint
CREATE TABLE "portfolio_snapshots" (
	"id" serial PRIMARY KEY NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"snapshot_at" timestamp with time zone DEFAULT now() NOT NULL,
	"total_value" numeric NOT NULL,
	"invested" numeric NOT NULL,
	"cash" numeric NOT NULL,
	"pnl" numeric NOT NULL,
	"pnl_pct" numeric NOT NULL,
	"holdings_json" text
);
--> statement-breakpoint
CREATE TABLE "screener_candidates" (
	"id" serial PRIMARY KEY NOT NULL,
	"scanned_at" timestamp with time zone DEFAULT now() NOT NULL,
	"stock_code" text NOT NULL,
	"stock_name" text NOT NULL,
	"pe_ratio" numeric,
	"dividend_yield" numeric,
	"roe" numeric,
	"composite_score" integer,
	"added_to_universe" boolean DEFAULT false NOT NULL
);
--> statement-breakpoint
CREATE TABLE "stock_prices" (
	"stock_id" text NOT NULL,
	"date" date NOT NULL,
	"open" numeric NOT NULL,
	"high" numeric NOT NULL,
	"low" numeric NOT NULL,
	"close" numeric NOT NULL,
	"volume" bigint DEFAULT 0 NOT NULL
);
--> statement-breakpoint
CREATE TABLE "stocks" (
	"id" text PRIMARY KEY NOT NULL,
	"name" text NOT NULL,
	"industry" text,
	"initial_price" numeric NOT NULL,
	"status" text DEFAULT 'active' NOT NULL,
	"kronos_warning" text,
	"added_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "trades" (
	"id" serial PRIMARY KEY NOT NULL,
	"portfolio_id" uuid NOT NULL,
	"stock_id" text NOT NULL,
	"action" text NOT NULL,
	"shares" integer NOT NULL,
	"price" numeric NOT NULL,
	"total_amount" numeric NOT NULL,
	"reason" text NOT NULL,
	"kronos_signal" text,
	"decision_source" text,
	"triggered_by" text,
	"snapshot_id" integer,
	"executed_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
CREATE TABLE "user_portfolios" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"user_id" uuid NOT NULL,
	"persona" text NOT NULL,
	"name" text NOT NULL,
	"strategy" text,
	"initial_capital" numeric DEFAULT '10000' NOT NULL,
	"cash" numeric DEFAULT '10000' NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL,
	"updated_at" timestamp with time zone DEFAULT now() NOT NULL,
	CONSTRAINT "uq_user_portfolio" UNIQUE("user_id","persona")
);
--> statement-breakpoint
CREATE TABLE "user_stock_picks" (
	"id" serial PRIMARY KEY NOT NULL,
	"user_id" uuid NOT NULL,
	"stock_id" text NOT NULL,
	"picked_at" timestamp with time zone DEFAULT now() NOT NULL,
	"picked_price" numeric NOT NULL,
	"note" text,
	"active" boolean DEFAULT true NOT NULL,
	CONSTRAINT "uq_user_stock_pick" UNIQUE("user_id","stock_id")
);
--> statement-breakpoint
CREATE TABLE "users" (
	"id" uuid PRIMARY KEY DEFAULT gen_random_uuid() NOT NULL,
	"name" text DEFAULT 'Kevin Mun' NOT NULL,
	"email" text,
	"default_capital" numeric DEFAULT '10000' NOT NULL,
	"notifications_enabled" boolean DEFAULT true NOT NULL,
	"created_at" timestamp with time zone DEFAULT now() NOT NULL
);
--> statement-breakpoint
ALTER TABLE "kronos_forecasts" ADD CONSTRAINT "kronos_forecasts_stock_id_stocks_id_fk" FOREIGN KEY ("stock_id") REFERENCES "public"."stocks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "portfolio_holdings" ADD CONSTRAINT "portfolio_holdings_portfolio_id_user_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "public"."user_portfolios"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "portfolio_holdings" ADD CONSTRAINT "portfolio_holdings_stock_id_stocks_id_fk" FOREIGN KEY ("stock_id") REFERENCES "public"."stocks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "portfolio_snapshots" ADD CONSTRAINT "portfolio_snapshots_portfolio_id_user_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "public"."user_portfolios"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "stock_prices" ADD CONSTRAINT "stock_prices_stock_id_stocks_id_fk" FOREIGN KEY ("stock_id") REFERENCES "public"."stocks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "trades" ADD CONSTRAINT "trades_portfolio_id_user_portfolios_id_fk" FOREIGN KEY ("portfolio_id") REFERENCES "public"."user_portfolios"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "trades" ADD CONSTRAINT "trades_stock_id_stocks_id_fk" FOREIGN KEY ("stock_id") REFERENCES "public"."stocks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "user_portfolios" ADD CONSTRAINT "user_portfolios_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "user_stock_picks" ADD CONSTRAINT "user_stock_picks_user_id_users_id_fk" FOREIGN KEY ("user_id") REFERENCES "public"."users"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
ALTER TABLE "user_stock_picks" ADD CONSTRAINT "user_stock_picks_stock_id_stocks_id_fk" FOREIGN KEY ("stock_id") REFERENCES "public"."stocks"("id") ON DELETE no action ON UPDATE no action;--> statement-breakpoint
CREATE INDEX "idx_kronos_stock" ON "kronos_forecasts" USING btree ("stock_id","generated_at");--> statement-breakpoint
CREATE INDEX "idx_snapshots_portfolio" ON "portfolio_snapshots" USING btree ("portfolio_id","snapshot_at");--> statement-breakpoint
CREATE INDEX "idx_prices_stock_date" ON "stock_prices" USING btree ("stock_id","date");--> statement-breakpoint
CREATE INDEX "idx_trades_portfolio" ON "trades" USING btree ("portfolio_id","executed_at");--> statement-breakpoint
CREATE INDEX "idx_trades_stock" ON "trades" USING btree ("stock_id");