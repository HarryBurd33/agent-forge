import { build } from "rolldown";
import { fileURLToPath } from "node:url";

await build({
  input: fileURLToPath(new URL("app.ts", import.meta.url)),
  platform: "browser",
  output: {
    file: fileURLToPath(new URL("../dist/fixture-browser/app.js", import.meta.url)),
    format: "esm",
    minify: true,
    // This generated bundle is local-only. Retain legal comments in it.
    comments: { legal: true },
  },
});
