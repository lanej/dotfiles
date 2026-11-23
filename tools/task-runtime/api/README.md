# Beads API source

`beads-1.3.4.yaml` is the MIT-licensed upstream contract from https://github.com/gastownhall/beads/blob/v1.3.4/internal/httpapi/spec/openapi.v0.yaml. Keep the pinned schema and generated TypeScript in the same change when updating Beads.

From `tools/task-runtime`, run `npm run generate:beads` to regenerate `generated/beads.ts` with the lockfile's `openapi-typescript`. `npm run check:beads-api` verifies that generated output matches this schema without contacting the service. The shared client uses `openapi-fetch` with these types; generation does not imply that the configured server implements every operation, so startup verifies the required capabilities.

The Neovim client uses the same schema. Run `npm run generate:beads-lua` to generate its operation descriptors, structural schemas and Lua annotations; `npm run check:beads-lua` checks freshness offline. The focused generator rejects unknown schema keywords rather than dropping contract information. Generated data drives the native Lua transport's parameter encoding and structural validation. Workspace policy and semantic constraints such as patterns/formats remain server-authoritative. Generation needs Node and the locked development dependencies; the editor needs only Neovim and curl, with no Node or Pi process.
