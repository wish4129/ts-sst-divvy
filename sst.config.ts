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
        allowMethods: ["GET"],
      },
    });

    api.route("GET /battle", "src/functions/battle.handler");

    new sst.aws.StaticSite("WebApp", {
      path: "web/",
      build: {
        output: "dist",
        command: "npm run build",
      },
      environment: {
        VITE_SUPABASE_URL: "https://ceyqewaixcijbmdtbdlr.supabase.co",
        VITE_SUPABASE_ANON_KEY: "eyJhbG...Kcbg",
        VITE_API_URL: api.url,
      },
    });
  },
});
