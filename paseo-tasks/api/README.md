# Beads API source

`beads-1.3.4.yaml` is the MIT-licensed upstream contract from https://github.com/gastownhall/beads/blob/v1.3.4/internal/httpapi/spec/openapi.v0.yaml. Keep the pinned schema and generated TypeScript in the same change when updating Beads.

From `paseo-tasks`, run `npm run generate:beads` to regenerate `../tools/task-runtime/generated/beads.ts` with the lockfile's `openapi-typescript`. `npm run check:beads-api` verifies that generated output matches this schema without contacting the service. The application uses `openapi-fetch` with these types; generation does not imply that the configured server implements every operation, so startup verifies the required capabilities.
