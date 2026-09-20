## What

Adding/updating: `providers/<provider>.yaml`

## Checklist

- [ ] `python3 scripts/catalog_validate.py providers/<provider>.yaml` passes locally
- [ ] I called at least one endpoint for real, with a real key
- [ ] `examples/<provider>.json` has a real captured response (key redacted)
- [ ] I tried a bad/missing key and filled in `auth.bad_key_behavior` with what actually happened
- [ ] `pricing.source_url` and `pricing.checked` point at the provider's real, current pricing page
- [ ] No real secret is pasted anywhere in this diff (the validator checks, but double check)

## Anything unusual about this provider?

(Auth quirks, undocumented rate limits, non-JSON responses, etc. — see CONTRIBUTING.md's
"Common traps" for examples of what's worth flagging here.)
