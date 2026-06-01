import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema/schema';

const client = postgres({
    host: process.env.DB_HOST!,
    port: parseInt(process.env.DB_PORT || '6543'),
    database: process.env.DB_NAME || 'postgres',
    username: process.env.DB_USER!,
    password: process.env.DB_PASSWORD!,
    ssl: 'require',
    max: 1,
    idle_timeout: 10,
    connect_timeout: 30,
    prepare: false,
    transform: { undefined: null }
});
export const db = drizzle(client, { schema });
