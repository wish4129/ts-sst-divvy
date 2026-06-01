import { drizzle } from 'drizzle-orm/postgres-js';
import postgres from 'postgres';
import * as schema from './schema/schema';

const connectionString = process.env.DATABASE_URL!;
const client = postgres(connectionString, {
    max: 1,
    idle_timeout: 10,
    connect_timeout: 30,
    prepare: false,
    transform: { undefined: null }
});
export const db = drizzle(client, { schema });
