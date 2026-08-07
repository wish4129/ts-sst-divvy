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

    api.route("GET /analysis/{code}", "src/functions/analysis.handler");
    api.route("GET /watchlist", "src/functions/watchlist.handler");
    api.route("GET /universe", "src/functions/universe.handler");
    api.route("POST /universe/add", "src/functions/universe.handler");
    api.route("POST /universe/request-analysis", "src/functions/universe.handler");
    api.route("POST /universe/search-log", "src/functions/universe.handler");
    api.route("POST /universe/click-log", "src/functions/universe.handler");
    api.route("GET /analytics/top-searches", "src/functions/universe.handler");
    api.route("GET /notes/{code}", "src/functions/notes.handler");
    api.route("POST /notes/{code}", "src/functions/notes.handler");
    api.route("GET /screener", "src/functions/screener.handler");
    api.route("GET /dividends", "src/functions/dividends.handler");
    // Sitemap is now served as a static file via CloudFront (web/public/sitemap.xml)
    // The pre-build script scripts/generate_sitemap.py runs before deployment.
    // Keep the Lambda handler as fallback for backward compatibility during transition.
    // api.route("GET /sitemap.xml", "src/functions/sitemap.handler");

    // CloudFront Function returning 410 Gone for the removed /battle route
    // Prevents Google from indexing the SPA fallback (200) as a live page
    const battleGoneFn = new aws.cloudfront.Function("BattleGoneFn", {
      name: "divvy-battle-gone-v1",
      runtime: "cloudfront-js-2.0",
      code: `function handler(event) {
  var request = event.request;
  if (request.uri === '/battle' || request.uri.startsWith('/battle?')) {
    return { statusCode: 410, statusDescription: 'Gone' };
  }
  return request;
}`,
      publish: true,
    });
    
    // CloudFront Function rewriting /stock/* to the SPA shell (index.html)
    // Fixes HTTP 403 (S3 OAC) on stock detail pages: SST's built-in SPA fallback
    // only rewrites extensionless paths — /stock/1155.KL looks like a file, so
    // CloudFront hits S3 directly, which has no matching key -> 403 XML.
    // Googlebot then cannot index any of the 800+ sitemap stock URLs.
    const stockSpaFallbackFn = new aws.cloudfront.Function("StockSpaFallbackFn", {
      name: "divvy-stock-spa-fallback-v1",
      runtime: "cloudfront-js-2.0",
      code: `function handler(event) {
  var request = event.request;
  if (request.uri.startsWith('/stock/')) {
    request.uri = '/index.html';
  }
  return request;
}`,
      publish: true,
    });

    // CloudFront Function returning noindex for the /cron/status route
    // Prevents Google from indexing the SPA fallback (index,follow) as a live page
    const cronStatusNoindexFn = new aws.cloudfront.Function("CronStatusNoindexFn", {
      name: "divvy-cron-status-noindex-v1",
      runtime: "cloudfront-js-2.0",
      code: `function handler(event) {
  var request = event.request;
  var response = { statusCode: 200, statusDescription: 'OK' };
  if (request.uri.startsWith('/cron/status')) {
    response.headers = { 'x-robots-tag': { value: 'noindex, follow' } };
    return response;
  }
  return request;
}`,
      publish: true,
    });

    new sst.aws.StaticSite("WebApp", {
      path: "web/",
      build: {
        output: "dist",
        command: "cd .. && uv run python3 scripts/generate_sitemap.py && cd web && npm run build",
      },
      environment: {
        VITE_SUPABASE_URL: "https://ceyqewaixcijbmdtbdlr.supabase.co",
        VITE_SUPABASE_ANON_KEY: "eyJhbG...Kcbg",
        VITE_API_URL: api.url,
      },
      transform: {
        cdn: (args, opts) => {
          // Add an edge function for /battle route to return 410 Gone
          // before the SPA fallback serves a 200 response
          args.orderedCacheBehaviors = [
            {
              // /stock/* -> SPA shell (index.html) via viewer-request rewrite.
              // Prevents S3 OAC 403 on stock detail pages (see StockSpaFallbackFn).
              pathPattern: "/stock*",
              targetOriginId: args.origins[0].originId,
              allowedMethods: ["GET", "HEAD", "OPTIONS"],
              cachedMethods: ["GET", "HEAD"],
              viewerProtocolPolicy: "redirect-to-https",
              compress: true,
              functionAssociations: [
                {
                  eventType: "viewer-request",
                  functionArn: stockSpaFallbackFn.arn,
                },
              ],
              forwardedValues: {
                queryString: false,
                cookies: { forward: "none" },
              },
              minTtl: 0,
              defaultTtl: 0,
              maxTtl: 0,
            },
            {
              pathPattern: "/battle*",
              targetOriginId: args.origins[0].originId,
              allowedMethods: ["GET", "HEAD", "OPTIONS"],
              cachedMethods: ["GET", "HEAD"],
              viewerProtocolPolicy: "redirect-to-https",
              compress: true,
              functionAssociations: [
                {
                  eventType: "viewer-request",
                  functionArn: battleGoneFn.arn,
                },
              ],
              forwardedValues: {
                queryString: false,
                cookies: { forward: "none" },
              },
              minTtl: 0,
              defaultTtl: 0,
              maxTtl: 0,
            },
            {
              pathPattern: "/cron/status*",
              targetOriginId: args.origins[0].originId,
              allowedMethods: ["GET", "HEAD", "OPTIONS"],
              cachedMethods: ["GET", "HEAD"],
              viewerProtocolPolicy: "redirect-to-https",
              compress: true,
              functionAssociations: [
                {
                  eventType: "viewer-request",
                  functionArn: cronStatusNoindexFn.arn,
                },
              ],
              forwardedValues: {
                queryString: false,
                cookies: { forward: "none" },
              },
              minTtl: 0,
              defaultTtl: 0,
              maxTtl: 0,
            },
          ];
        },
      },
    });
  },
});
