# GitHub Actions CI/CD — Rules and Lessons Learned

This project has two workflows in `.github/workflows/`. Both deploy automatically on push to `master`.

## Workflow triggers

- `backend.yml` — triggers when `SamLambda/**` or `.github/workflows/backend.yml` changes
- `frontend.yml` — triggers when `FrontEndCode/**` or `.github/workflows/frontend.yml` changes

An empty commit (`git commit --allow-empty`) will NOT trigger either workflow — it must touch a file in the relevant path.

## SAM validate and linting

`sam validate --lint` uses cfn-lint under the hood. Lint failures exit with code 1 and block the deploy.

The W3660 warning fires because this project defines both an inline API `Body` and `GatewayResponse` resources — this is intentional and safe. It is suppressed via `SamLambda/.cfnlintrc`:

```yaml
ignore_checks:
  - W3660
```

Do not remove `.cfnlintrc`. Do not add `--ignore-checks` to the `sam validate` command — that flag does not exist.

## Amplify deployment

The Amplify app ID is `d33jt7rnrasyvj`. The connected branch is `main` (not `master`).

The frontend workflow:
1. Builds the app with `npm run build` in `FrontEndCode/`
2. Zips the output: `zip -r dist.zip .` run from inside `FrontEndCode/dist/` — so the zip lands at `FrontEndCode/dist/dist.zip`
3. Calls `aws amplify create-deployment --branch-name main`
4. Uploads the zip via the pre-signed URL using curl: path must be `FrontEndCode/dist/dist.zip`
5. Calls `aws amplify start-deployment`

## Stuck Amplify jobs

Amplify only allows one active deployment at a time. If a previous run failed mid-deploy, it leaves a PENDING or RUNNING job that blocks the next `create-deployment` with:

```
BadRequestException: The last job(deployment) N was not finished
```

The workflow auto-cancels stuck jobs before creating a new deployment. If you ever need to do it manually:

```bash
aws amplify stop-job --app-id d33jt7rnrasyvj --branch-name main --job-id <N>
```

## GitHub Actions first-run quirk

When workflow files are first pushed to a repo, GitHub may not trigger a run for that exact commit. To force a trigger, make a real file change inside the relevant path (`SamLambda/**` or `FrontEndCode/**`) and push again.

## Workflow file changes and commit timing

GitHub Actions runs the workflow version from the commit that triggered the run — not the latest on the branch. If you fix a workflow file and push it in a separate commit from the file that triggered the run, the fix won't apply to that run. Always verify which commit SHA a failing run is using before assuming the fix was picked up.

## ESLint in CI

The frontend workflow runs `npm run lint` before building. Pre-existing lint errors in auto-generated shadcn `ui/` components and other files will block the build. These rules are turned off in `FrontEndCode/eslint.config.js`:

- `@typescript-eslint/no-explicit-any`
- `@typescript-eslint/no-empty-object-type`
- `@typescript-eslint/no-require-imports`
- `no-case-declarations`

Do not re-enable these without fixing all the violations first.

## Required GitHub secrets

All secrets are documented in `.github/SECRETS.md`. The IAM user is `soulreel-github-actions`. If AWS credentials stop working, check that user's access keys in IAM — do not create a new user, just rotate the keys and update the `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` secrets in GitHub.
