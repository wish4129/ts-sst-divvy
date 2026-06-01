import { defineConfig } from "drizzle-kit";

export default defineConfig({
    schema: './src/schema/schema.ts',
    out: './src/schema/migrations',
    dialect: 'postgresql',
    dbCredentials: {
        host: process.env.DB_HOST!,
        port: parseInt(process.env.DB_PORT || '6543'),
        database: process.env.DB_NAME || 'postgres',
        user: process.env.DB_USER!,
        password: process.env.DB_PASSWORD!,
        ssl: 'require',
    },
});
