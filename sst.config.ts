/// <reference path="./.sst/platform/config.d.ts" />

export default $config({
  app(input) {
    return {
      name: "divvy",
      removal: input?.stage === "live" ? "retain" : "remove",
      home: "aws",
      profile: "xion",
      region: "ap-southeast-1",
    };
  },
  async run() {
    const api = new sst.aws.ApiGatewayV2("Api", {
      cors: {
        allowOrigins: ["*"],
        allowMethods: ["GET", "POST"],
      },
    });

    api.route("GET /battle", "src/functions/battle.handler");
    api.route("GET /analysis/{code}", "src/functions/analysis.handler");
    api.route("GET /watchlist", "src/functions/watchlist.handler");
    api.route("GET /universe", "src/functions/universe.handler");
    api.route("POST /universe/add", "src/functions/universe.handler");
    api.route("POST /universe/request-analysis", "src/functions/universe.handler");
    api.route("GET /notes/{code}", "src/functions/notes.handler");
    api.route("POST /notes/{code}", "src/functions/notes.handler");
    api.route("GET /screener", "src/functions/screener.handler");
    api.route("GET /sitemap.xml", "src/functions/sitemap.handler");

    new sst.aws.StaticSite("WebApp", {
      path: "web/",
      build: {
        output: "dist",
        command: "npm run build",
      },
      environment: {
        VITE_SUPABASE_URL: "https://ceyqewaixcijbmdtbdlr.supabase.co",
        VITE_SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXFld2FpeGNpamJtZHRiZGxyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMTM4MDcsImV4cCI6MjA5NTg4OTgwN30.gW5MKzdMMUrzGq--NekVSsJT07KlQ_O0skrRjSHKcbg",
        VITE_API_URL: api.url,
      },
    });
  },
});
