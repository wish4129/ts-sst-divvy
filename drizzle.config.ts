import { defineConfig } from "drizzle-kit";

export default defineConfig({
    schema: './src/schema/schema.ts',
    out: './src/schema/migrations',
    dialect: 'postgresql',
    dbCredentials: {
        url: process.env.DATABASE_URL!,
    },
});
