---
inclusion: always
---

# Lambda IAM Permissions — Rules and Checklist

IAM permission errors cause silent failures that surface as generic "server error" messages to users.
They are easy to introduce and hard to spot without checking CloudWatch logs.

## The core rule

When you change HOW a Lambda function calls an AWS API, you must also update its IAM policy.
AWS IAM actions are granular — singular, plural, and batch variants are separate permissions.

**The code change and the IAM policy change must be in the same deploy.**

## Dangerous method swaps — always check IAM when doing these

| Old call | New call | Old IAM action needed | New IAM action also needed |
|---|---|---|---|
| `ssm.get_parameter()` | `ssm.get_parameters()` | `ssm:GetParameter` | `ssm:GetParameters` |
| `dynamodb.get_item()` | `dynamodb.batch_get_item()` | `dynamodb:GetItem` | `dynamodb:BatchGetItem` |
| `dynamodb.put_item()` | `dynamodb.batch_write_item()` | `dynamodb:PutItem` | `dynamodb:BatchWriteItem` |
| `dynamodb.delete_item()` | `dynamodb.batch_write_item()` | `dynamodb:DeleteItem` | `dynamodb:BatchWriteItem` |
| `dynamodb.query()` | `dynamodb.scan()` | `dynamodb:Query` | `dynamodb:Scan` |
| `s3.get_object()` | `s3.list_objects()` | `s3:GetObject` | `s3:ListBucket` |

## Checklist when modifying a Lambda function's AWS API calls

- [ ] Did you change which boto3 method is called? If yes, check the IAM policy in `template.yml`
- [ ] Does the IAM policy grant the exact action name for the new method?
- [ ] If you added a new AWS service call (e.g. Lambda now calls SES for the first time), is there a policy statement for it?
- [ ] After deploy, check CloudWatch logs for `AccessDeniedException` on the first few invocations

## Where IAM policies live in this project

All Lambda IAM policies are inline in `SamLambda/template.yml` under each function's `Policies` block.
Search for the function name, then look for the `Statement` list below it.

The WebSocketDefaultFunction policy is around line 700 in `template.yml`.

## How to verify after a deploy

Check CloudWatch for access errors within a few minutes of deploying:

```bash
aws logs filter-log-events \
  --log-group-name "/aws/lambda/Virtual-Legacy-MVP-1-WebSocketDefaultFunction-ovGSm9iorpVb" \
  --start-time $(date -v-10M +%s000) \
  --filter-pattern "AccessDeniedException" \
  --query "events[*].message" \
  --output text
```

Replace the log group name with the relevant function. Any `AccessDeniedException` means a missing IAM action.

## Known past incidents

- **Mar 2026**: Phase 2 refactor changed `ssm.get_parameter()` to `ssm.get_parameters()` (batch) for performance.
  IAM policy had `ssm:GetParameter` but not `ssm:GetParameters`. Every conversation start failed with
  `AccessDeniedException`, surfacing to users as "A server error occurred. Please try again."
  Fix: added `ssm:GetParameters` alongside `ssm:GetParameter` in the WebSocketDefaultFunction policy.
