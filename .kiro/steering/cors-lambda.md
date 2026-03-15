---
inclusion: always
---

# CORS in Lambda + API Gateway — Rules and Checklist

This project uses AWS SAM with Cognito-authorized API Gateway. CORS has broken multiple times.
Every time a Lambda function or API Gateway config is touched, follow these rules.

## How CORS works in this project

There are THREE layers that must all be consistent:

1. **SAM template `Globals.Api.Cors`** — controls API Gateway's automatic OPTIONS response at the gateway level
2. **SAM template `GatewayResponse` resources** (Unauthorized, Default4XX, Default5XX) — controls CORS headers on error responses that never reach Lambda
3. **Each Lambda function's response headers** — every response (200, 4XX, 5XX) must include `Access-Control-Allow-Origin`

All three must use the same origin. The allowed origin is `https://www.soulreel.net`.

## The `ALLOWED_ORIGIN` env var

The SAM Globals sets `ALLOWED_ORIGIN` as an environment variable on every Lambda function.
Lambda functions read it via `os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')`.

**Critical**: Any Lambda file that uses `os.environ` MUST have `import os` at the top.
This has caused 502 errors on OPTIONS preflight before — missing `import os` causes a NameError
that crashes the function and returns no CORS headers.

## Checklist when adding or modifying a Lambda function

- [ ] `import os` is present at the top of `app.py`
- [ ] Every response dict includes `'Access-Control-Allow-Origin': os.environ.get('ALLOWED_ORIGIN', 'https://www.soulreel.net')`
- [ ] The OPTIONS preflight case is handled (either via SAM's automatic CORS or an explicit `if event.get('httpMethod') == 'OPTIONS':` block)
- [ ] If handling OPTIONS manually, the handler also uses `os.environ.get('ALLOWED_ORIGIN', ...)` — not a hardcoded string

## Checklist when changing the allowed origin (e.g. new domain)

When the frontend domain changes, ALL of the following must be updated together and redeployed:

- [ ] `Globals.Function.Environment.Variables.ALLOWED_ORIGIN` in `SamLambda/template.yml`
- [ ] `Globals.Api.Cors.AllowOrigin` in `SamLambda/template.yml`
- [ ] `GatewayResponseUnauthorized` `Access-Control-Allow-Origin` in `SamLambda/template.yml`
- [ ] `GatewayResponseDefault4XX` `Access-Control-Allow-Origin` in `SamLambda/template.yml`
- [ ] `GatewayResponseDefault5XX` `Access-Control-Allow-Origin` in `SamLambda/template.yml`
- [ ] `DEPLOYMENT_INFO.txt` CORS section
- [ ] Run `sam build && sam deploy --no-confirm-changeset` from `SamLambda/`

The Lambda function source files do NOT need to be changed when the domain changes — they read
from the env var. Only the template needs updating.

## How to verify CORS is working after a deploy

Run this curl command — it tests the OPTIONS preflight directly, bypassing browser cache:

```bash
curl -X OPTIONS "https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod/streak" \
  -H "Origin: https://www.soulreel.net" \
  -H "Access-Control-Request-Method: GET" \
  -v 2>&1 | grep -i "access-control\|< HTTP"
```

Expected output:
```
< HTTP/2 200
< access-control-allow-origin: https://www.soulreel.net
< access-control-allow-headers: ...
< access-control-allow-methods: ...
```

If you get a 502, the Lambda is crashing on OPTIONS — check for missing `import os`.
If you get a 200 but with the wrong origin, the env var wasn't updated or the deploy didn't propagate.
If the browser still fails after curl succeeds, it's a browser preflight cache issue — test in a private window.

## Known past incidents

- **Feb 2026**: CORS wildcard `*` replaced with specific origin as security fix — correct change
- **Mar 2026**: Custom domain `www.soulreel.net` added but CORS origin not updated from `main.d33jt7rnrasyvj.amplifyapp.com` — caused dashboard to fail for all users
- **Mar 2026**: Previous session added `os.environ.get('ALLOWED_ORIGIN', ...)` to 17 Lambda files but forgot `import os` — every OPTIONS preflight returned 502, CORS appeared broken even after domain fix
