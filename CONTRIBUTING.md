# Contributing

Thanks for adding a tool. This catalog stays useful only if every entry reflects
a real, working API — so the bar is: **could a stranger read this file and
successfully call the tool on the first try, with no other docs open?**

**This guide covers `providers/*.yaml` only.** `models/*.yaml` (muapi's own hosted
models) is auto-generated from muapi's live catalog and isn't a PR target — see
the README's "muapi-hosted models" section. If you want a model added there or
think one is wrong, open an issue instead of a PR.

## Before you start

- Do you have a real (even free-tier) key for this provider? You'll need one —
  see "The live test" below. If you can't get a key, don't open the PR yet.
- Does the provider already have an entry? Check `providers/` first — a
  near-duplicate with no distinct value gets rejected.

## Selection rules

A tool is accepted when:

- **Self-serve.** Sign up, get a key, start calling — no sales call, no approval
  wait beyond normal email/API-key issuance.
- **Distinct value.** It does something the catalog doesn't already cover, or
  covers it meaningfully differently (price, coverage, data freshness).
- **Publicly priced**, or clearly and permanently free within a stated limit.

A tool is rejected, with a reason recorded in the PR thread, when it's:

- enterprise/sales-gated with no public self-serve tier,
- deprecated or the docs are stale/dead,
- UI-only with no real API behind it,
- a near-duplicate of an existing entry with no meaningful difference.

If you're not sure a tool clears the bar, open an issue first rather than a PR —
cheaper for everyone if the answer is no.

## Filling out the entry

1. Copy `providers/_TEMPLATE.yaml` → `providers/<provider>.yaml` (lowercase,
   hyphenated, matching the provider's common name — e.g. `providers/hunter.yaml`).
2. Fill every required field from the provider's **own published docs** — don't
   guess. Leave `note` fields for anything non-obvious (a quirky auth header, a
   rate limit that isn't documented anywhere clean, a param that silently no-ops).
3. Fill `pricing` from the provider's actual pricing page, with a `source_url`
   and today's date in `checked`.

## The live test (required, no exceptions)

**Never submit an entry you haven't watched actually work.** Specifically:

1. Get a real key (free tier is fine).
2. Call at least one endpoint for real.
3. Capture the real response into `examples/<id>.json` (redact the key itself,
   keep everything else — that's what makes the entry trustworthy).
4. Also try one call with a deliberately bad/missing key and note what the
   provider actually returns in `auth.bad_key_behavior` — some APIs return a
   200 with an error body instead of a 401/403, which silently breaks anything
   that checks status codes. Write down what you saw, not what you'd expect.

A PR without a captured `examples/<id>.json` is submitted as `status: draft` at
best and won't be merged as `verified`.

## Validate before opening the PR

```bash
python3 scripts/catalog_validate.py providers/<your-provider>.yaml
```

This checks schema shape, required fields, id conventions, and — importantly —
scans for anything that looks like a real secret accidentally left in the file
or its example. Fix everything it flags before opening the PR; CI runs the same
check and will block the merge otherwise.

## Common traps (read before you get surprised by one)

- **200 on a bad key.** Some APIs return `200` with an error message in the body
  instead of an HTTP error status. Don't assume status-code-only error handling
  works — check the actual body shape.
- **Trailing-slash redirects.** A `301`/`308` on a missing/extra trailing slash
  can silently strip an `Authorization` header on redirect with some HTTP
  clients. Note the exact path shape that works.
- **Key-in-path.** A few providers embed the key in the URL path rather than a
  header or query param — note this explicitly, it's easy to miss.
- **CSV/non-JSON bodies.** Some "REST" APIs return CSV or XML for specific
  endpoints. Say so in the endpoint's `note` rather than assuming JSON.

## After merge

A maintainer independently re-runs your live test before flipping `status` to
`verified`. This can take a few days — a merged PR with `status: draft` is
expected in the meantime, not a rejection.
