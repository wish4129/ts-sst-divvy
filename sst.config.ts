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
    });
  },
});
