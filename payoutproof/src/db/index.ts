import { drizzle } from "drizzle-orm/node-postgres";
import { Pool } from "pg";
import * as schema from "./schema";
import { env } from "../lib/env";

let pool: Pool | undefined;

/** Lazy singleton pool — created on first use so tests/builds don't connect. */
export function getDb() {
  if (!pool) {
    pool = new Pool({ connectionString: env.databaseUrl, max: 10 });
  }
  return drizzle(pool, { schema });
}

export { schema };
export type Db = ReturnType<typeof getDb>;
