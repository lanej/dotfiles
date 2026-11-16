# Cloud Run access and ephemeral analysis

## Cloud Run native IAP — programmatic access and ingress vs. auth

- **The default Google-managed IAP OAuth client blocks all OAuth-ID-token
  programmatic access**, human or service account — `gcloud auth
  print-identity-token --audiences=<iap-url>` fails outright for both. A
  **service-account self-signed JWT** is a different credential type that
  bypasses the OAuth client entirely and IAP accepts it directly: `iss`/`sub`
  = the SA's email, signed via `gcloud iam service-accounts sign-jwt` (or the
  IAM Credentials API's `signJwt`, no private key file needed). The SA needs
  `roles/iam.serviceAccountTokenCreator` on itself (to sign) and
  `roles/iap.httpsResourceAccessor` on the specific IAP resource. This is the
  right pattern for one Cloud Run service calling another IAP-protected one,
  without provisioning a custom OAuth client just to unblock ID tokens.
- **The JWT's `aud` claim must equal the exact request path IAP is checking
  against, not just the service's base URL.** A JWT minted with `aud =
  https://svc.run.app` can pass IAP on `GET /` (which resolves to the base
  URL) while failing on `POST /verify` or any other path, with "Audience
  specified does not match requested endpoint." Mint (or re-mint) the JWT
  with the full target path as `aud` for every distinct endpoint you call —
  don't assume one token scoped to the host works for all routes.
- **`ingress` (network reachability) and auth are different layers — don't
  conflate them.** `INGRESS_TRAFFIC_ALL` (the default) means the service's
  `*.run.app` URL is directly dialable from the public internet at the
  connection level regardless of what auth sits in front of it (IAP, bare
  `run.invoker` IAM); the auth layer is what then accepts/rejects the
  request. Only `INGRESS_TRAFFIC_INTERNAL_ONLY` makes the service genuinely
  un-dialable from outside — and Cloud-Run-to-Cloud-Run traffic is **not**
  automatically "internal" just because both live in the same project: it
  requires an actual VPC path (Serverless VPC Access connector or Direct VPC
  egress) on the caller, which most single-service Cloud Run setups don't
  have. Flipping ingress to internal-only also blocks IAP's own browser-login
  path and any caller outside that VPC (e.g. a laptop) — a bare-IAM or IAP
  auth gate on top of `INGRESS_TRAFFIC_ALL` is often the correct trade for a
  low-traffic internal tool, not a lesser version of "actually internal."

## Ephemeral Cloud Run Job for One-off Server-Side GCS Analysis

When a one-off analysis needs to read a GCS bucket too large to download locally (tens of GB/day across many days), don't download it — run a scoped, disposable Cloud Run Job against it and tear the job down afterward:

1. If the bucket lives in a different project than your deploy target, that's a cross-project IAM
   grant and needs explicit user approval first — not a same-project additive apply (see the
   infra-apply-approval-scope rule).
2. Create a **new, dedicated** service account for this job only — never the shared default
   compute SA — and grant it read access (`roles/storage.objectViewer`) on the **specific bucket
   only**, not project-wide.
3. Stream directly against GCS (`gsutil cat` piped to your processor) — nothing should land on
   local disk or in a persistent bucket. Parallelize with one task per unit of work.
4. After collecting results, delete the job, the service account, and the IAM binding, and
   **independently verify each deletion** (`gcloud run jobs describe` → not found,
   `gcloud iam service-accounts list` → zero matches, `gsutil iam get` on the bucket → binding
   gone) rather than trusting a sub-agent's cleanup report.

(detail: memory "project_ep67_cloud_run_ephemeral_analysis_job")

## Cloud Run — Multi-Container & Job Gotchas

For Cloud SQL proxy sidecars, multi-container resource limits and flags, job argument overrides, or deployment verification, read [Cloud Run job and deployment notes](cloud-run-jobs.md).
