import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { Pool } from "pg";
import { env } from "../src/lib/env";

/** Apply drizzle/*.sql migrations in order. Run: tsx scripts/migrate.ts */
async function main() {
  const dir = join(process.cwd(), "drizzle");
  const files = readdirSync(dir)
    .filter((f) => f.endsWith(".sql"))
    .sort();
  const pool = new Pool({ connectionString: env.databaseUrl });
  await pool.query(
    "CREATE TABLE IF NOT EXISTS _migrations (name text primary key, applied_at timestamptz default now())",
  );
  for (const file of files) {
    const { rowCount } = await pool.query("SELECT 1 FROM _migrations WHERE name = $1", [file]);
    if (rowCount) {
      console.log(`skip ${file}`);
      continue;
    }
    const sql = readFileSync(join(dir, file), "utf8");
    console.log(`apply ${file}`);
    await pool.query(sql);
    await pool.query("INSERT INTO _migrations(name) VALUES ($1)", [file]);
  }
  await pool.end();
  console.log("Migrations complete.");
  process.exit(0);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
