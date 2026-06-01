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
    const dbPassword = new sst.Secret("DBPassword");

    const api = new sst.aws.ApiGatewayV2("Api", {
      cors: {
        allowOrigins: ["*"],
        allowMethods: ["GET"],
      },
    });

    api.route("GET /battle", "src/functions/battle.handler", {
      environment: {
        DB_HOST: "aws-1-ap-northeast-1.pooler.supabase.com",
        DB_PORT: "6543",
        DB_NAME: "postgres",
        DB_USER: "postgres.ceyqewaixcijbmdtbdlr",
        DB_PASSWORD: dbPassword.value,
      },
    });

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
