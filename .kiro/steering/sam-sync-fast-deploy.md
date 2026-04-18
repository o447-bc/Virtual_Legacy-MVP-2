---
inclusion: fileMatch
fileMatchPattern: ".github/workflows/backend.yml"
---

# SAM Sync for Fast Code-Only Deploys

The backend workflow in `.github/workflows/backend.yml` currently uses `sam deploy` for every push.
With 69 Lambda functions, CloudFormation takes ~3 minutes just to roll through the update.
`sam sync --code` bypasses CloudFormation entirely and updates Lambda function code directly — cutting deploy from ~3 min to ~30s for code-only changes.

## When to use `sam sync --code` vs `sam deploy`

- **Code-only changes** (Python files in `functions/`, shared layer code): use `sam sync --code --stack-name Virtual-Legacy-MVP-1`
- **Infrastructure changes** (template.yml resources, IAM policies, API Gateway config, new functions, environment variables): use `sam deploy`

If both code and infra changed in the same push, always use `sam deploy`. When in doubt, use `sam deploy`.

## How to detect code-only vs infra changes

Use `git diff` against the previous commit to check if `template.yml` changed:

```bash
TEMPLATE_CHANGED=$(git diff --name-only HEAD~1 HEAD -- SamLambda/template.yml | wc -l)
if [ "$TEMPLATE_CHANGED" -eq "0" ]; then
  # Code-only — safe to use sam sync
  sam sync --code --stack-name Virtual-Legacy-MVP-1 --no-watch --region us-east-1
else
  # Infra changed — must use full deploy
  sam deploy --no-confirm-changeset --no-fail-on-empty-changeset
fi
```

## IAM requirements for `sam sync`

`sam sync` needs the same permissions as `sam deploy` plus `lambda:UpdateFunctionCode`.
The OIDC role (`AWS_DEPLOY_ROLE_ARN`) already has this via the CloudFormation deploy permissions.
No IAM changes are needed.

## Important constraints

- `sam sync --code` still requires `sam build` to run first — it reads from `.aws-sam/build/`.
- `sam sync` does NOT run CloudFormation validation. Template errors won't be caught until the next full deploy. Keep `sam validate --lint` in the pipeline regardless.
- `sam sync` does NOT update environment variables, IAM policies, or event sources. Those live in CloudFormation and require `sam deploy`.
- Always pass `--no-watch` in CI. Without it, `sam sync` enters watch mode and hangs forever.

## What NOT to do

- Do not remove the `sam deploy` path. Infra changes must go through CloudFormation.
- Do not skip `sam build` before `sam sync`. It needs the built artifacts.
- Do not skip `sam validate --lint`. It catches template errors that `sam sync` would silently ignore.
- Do not use `sam sync` without `--stack-name`. It will prompt interactively and hang in CI.

## Known risk

If someone pushes a code change that depends on a template change (e.g., new env var) but only the code file is in the commit, `sam sync --code` will deploy the code without the env var. The function will fail at runtime. Mitigation: always push code + template changes in the same commit.
