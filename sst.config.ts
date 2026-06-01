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
    new sst.aws.StaticSite("WebApp", {
      path: "web/",
      build: {
        output: "dist",
        command: "npm run build",
      },
      environment: {
        VITE_SUPABASE_URL: "https://ceyqewaixcijbmdtbdlr.supabase.co",
        VITE_SUPABASE_ANON_KEY: "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNleXFld2FpeGNpamJtZHRiZGxyIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODAzMTM4MDcsImV4cCI6MjA5NTg4OTgwN30.gW5MKzdMMUrzGq--NekVSsJT07KlQ_O0skrRjSHKcbg",
      },
    });
  },
});
