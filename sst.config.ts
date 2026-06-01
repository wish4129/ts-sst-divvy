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
    const supabaseUrl = "https://ceyqewaixcijbmdtbdlr.supabase.co";
    const supabaseAnonKey = process.env.SUPABASE_ANON_KEY!;
    const databaseUrl = process.env.DATABASE_URL!;

    new sst.aws.StaticSite("WebApp", {
      path: "web/",
      build: {
        output: "dist",
        command: "npm run build",
      },
      environment: {
        VITE_SUPABASE_URL: supabaseUrl,
        VITE_SUPABASE_ANON_KEY: supabaseAnonKey,
      },
    });
  },
});
