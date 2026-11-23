import { readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import { parse } from "smol-toml";
import { z } from "zod";

export const defaultMinSplitColumns = 40;
const schema = z.strictObject({
  diff: z
    .strictObject({
      min_split_columns: z
        .number()
        .int()
        .positive()
        .default(defaultMinSplitColumns),
    })
    .default({ min_split_columns: defaultMinSplitColumns }),
});

export async function loadDiffDisplayConfig() {
  const path = join(
    process.env["XDG_CONFIG_HOME"] ?? join(homedir(), ".config"),
    "pi-driver/display.toml",
  );
  try {
    return schema.parse(parse(await readFile(path, "utf8"))).diff;
  } catch (error) {
    if (z.object({ code: z.literal("ENOENT") }).safeParse(error).success)
      return schema.parse({}).diff;
    throw new Error(
      `Cannot load Pi driver display configuration ${path}: ${error instanceof Error ? error.message : String(error)}`,
    );
  }
}
