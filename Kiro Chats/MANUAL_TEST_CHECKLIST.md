# Manual Test Checklist: Legacy Maker Benefactor Assignment

> Replace `YOUR_API_URL`, `$TOKEN`, `$BENEFACTOR_TOKEN`, `MAKER_ID`, `BENEFACTOR_ID` with your actual values before running.

---

## Setup

- [ ] Logged in as Legacy Maker and have JWT token saved as `$TOKEN`
- [ ] Have a registered benefactor email in Cognito (e.g. `benefactor@test.com`)
- [ ] Have an unregistered email ready (e.g. `new@test.com`) — must NOT exist in Cognito
- [ ] API Gateway URL known

**Get token via CLI:**
```bash
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=your@email.com,PASSWORD=YourPassword
# Save the IdToken as TOKEN
```

---

## 1. Create Assignment — Registered Benefactor (Immediate Access)

- [ ] Run the request:
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "benefactor@test.com", "access_conditions": [{"condition_type": "immediate"}]}'
```
- [ ] Response is 200
- [ ] Response contains `assignment_id`
- [ ] `invitation_sent` is `true`
- [ ] `invitation_token` is `null` (registered user, no token needed)
- [ ] Benefactor receives notification email

---

## 2. Create Assignment — Unregistered Benefactor (Invitation Flow)

- [ ] Run the request:
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "new@test.com", "access_conditions": [{"condition_type": "immediate"}]}'
```
- [ ] Response is 200
- [ ] `invitation_token` is a UUID (not null)
- [ ] `invitation_sent` is `true`
- [ ] Invitation email received at `new@test.com`
- [ ] Email contains registration link with token

**Verify in DynamoDB:**
```bash
aws dynamodb scan \
  --table-name PersonaSignupTempDB \
  --filter-expression "invitee_email = :email" \
  --expression-attribute-values '{":email": {"S": "new@test.com"}}'
```
- [ ] Token record exists in PersonaSignupTempDB
- [ ] TTL is set (~7 days)

---

## 3. Create Assignment — Time-Delayed Access

- [ ] Run the request:
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "benefactor@test.com", "access_conditions": [{"condition_type": "time_delayed", "activation_date": "2026-12-31T23:59:59Z"}]}'
```
- [ ] Response is 200
- [ ] `conditions_created` is 1
- [ ] Condition type is `time_delayed` in response

---

## 4. Create Assignment — Multiple Conditions

- [ ] Run the request:
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "benefactor@test.com",
    "access_conditions": [
      {"condition_type": "time_delayed", "activation_date": "2026-06-01T00:00:00Z"},
      {"condition_type": "inactivity_trigger", "inactivity_months": 12, "check_in_interval_days": 30},
      {"condition_type": "manual_release"}
    ]
  }'
```
- [ ] Response is 200
- [ ] `conditions_created` is 3

---

## 5. Duplicate Assignment (Should Fail)

- [ ] Run the same create request from Test 1 again (same benefactor email)
- [ ] Response is 409 Conflict
- [ ] Error message says assignment already exists

---

## 6. Validation Errors (Should Fail)

**6a — Past date:**
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "benefactor@test.com", "access_conditions": [{"condition_type": "time_delayed", "activation_date": "2020-01-01T00:00:00Z"}]}'
```
- [ ] Response is 400
- [ ] Error mentions activation date must be in the future

**6b — Inactivity months too high:**
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "benefactor@test.com", "access_conditions": [{"condition_type": "inactivity_trigger", "inactivity_months": 30}]}'
```
- [ ] Response is 400
- [ ] Error mentions 24 month limit

**6c — No conditions:**
```bash
curl -X POST https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "benefactor@test.com", "access_conditions": []}'
```
- [ ] Response is 400
- [ ] Error says at least one condition required

---

## 7. Get Assignments

- [ ] Run the request:
```bash
curl -X GET https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN"
```
- [ ] Response is 200
- [ ] `assignments` array is present
- [ ] `count` matches number of assignments
- [ ] Registered benefactors show `account_status: "registered"`
- [ ] Unregistered benefactors show `account_status: "invitation_pending"`
- [ ] Each assignment includes `access_conditions` array

---

## 8. Benefactor Accept Assignment

- [ ] Log in as benefactor and get `$BENEFACTOR_TOKEN`
- [ ] Run the request:
```bash
curl -X POST https://YOUR_API_URL/assignments/respond \
  -H "Authorization: Bearer $BENEFACTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "accept", "initiator_id": "MAKER_ID"}'
```
- [ ] Response is 200
- [ ] Legacy Maker receives confirmation email
- [ ] Get assignments again — `assignment_status` is now `active`

---

## 9. Benefactor Decline Assignment

- [ ] Run the request (use a different/fresh assignment):
```bash
curl -X POST https://YOUR_API_URL/assignments/respond \
  -H "Authorization: Bearer $BENEFACTOR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "decline", "initiator_id": "MAKER_ID"}'
```
- [ ] Response is 200
- [ ] Assignment status updated to `declined`

---

## 10. Validate Access

**Before acceptance (should be denied):**
```bash
curl -X GET "https://YOUR_API_URL/validate-access?requestingUserId=BENEFACTOR_ID&targetUserId=MAKER_ID" \
  -H "Authorization: Bearer $BENEFACTOR_TOKEN"
```
- [ ] `hasAccess` is `false`

**After acceptance with immediate condition:**
- [ ] `hasAccess` is `true`
- [ ] `reason` is `relationship_access`

---

## 11. Manual Release

- [ ] Create an assignment with `manual_release` condition and have benefactor accept it
- [ ] Verify access is denied first (validate-access returns false)
- [ ] Trigger release:
```bash
curl -X POST https://YOUR_API_URL/assignments/manual-release \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
```
- [ ] Response is 200, `releases_processed` is 1
- [ ] Validate access again — `hasAccess` is now `true`
- [ ] Benefactor receives access granted email
- [ ] Run release again — `releases_processed` is 0 (idempotent)

---

## 12. Update Assignment Conditions (Pending Only)

- [ ] Create a pending assignment
- [ ] Update conditions:
```bash
curl -X PUT https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "update_conditions", "related_user_id": "BENEFACTOR_ID", "access_conditions": [{"condition_type": "manual_release"}]}'
```
- [ ] Response is 200, conditions updated
- [ ] Try same update on an active assignment — response is 400/error

---

## 13. Revoke Active Assignment

- [ ] Have an active assignment (accepted by benefactor)
- [ ] Revoke it:
```bash
curl -X PUT https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "revoke", "related_user_id": "BENEFACTOR_ID"}'
```
- [ ] Response is 200
- [ ] Validate access immediately — `hasAccess` is `false`
- [ ] Benefactor receives revocation email
- [ ] DynamoDB shows `status: "revoked"`

---

## 14. Delete Pending Assignment

- [ ] Create a new pending assignment
- [ ] Delete it:
```bash
curl -X PUT https://YOUR_API_URL/assignments \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"action": "delete", "related_user_id": "BENEFACTOR_ID"}'
```
- [ ] Response is 200
- [ ] Assignment no longer appears in GET /assignments
- [ ] Try deleting an active assignment — response is error

---

## 15. Resend Invitation

- [ ] Create assignment for unregistered benefactor
- [ ] Resend invitation:
```bash
curl -X POST https://YOUR_API_URL/assignments/resend-invitation \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"benefactor_email": "new@test.com"}'
```
- [ ] Response is 200
- [ ] New invitation email received
- [ ] New token exists in PersonaSignupTempDB with fresh TTL

---

## 16. Scheduled Jobs (Manual Invocation)

**Time Delay Processor:**
```bash
aws lambda invoke --function-name TimeDelayProcessorFunction --payload '{}' response.json && cat response.json
```
- [ ] Returns 200
- [ ] `activations_processed` and `successful_activations` in response

**Check-In Sender:**
```bash
aws lambda invoke --function-name CheckInSenderFunction --payload '{}' response.json && cat response.json
```
- [ ] Returns 200
- [ ] `check_ins_sent` in response
- [ ] Check-in email received at Legacy Maker's email with verification link

**Inactivity Processor:**
```bash
aws lambda invoke --function-name InactivityProcessorFunction --payload '{}' response.json && cat response.json
```
- [ ] Returns 200
- [ ] `activations_processed` in response

---

## 17. Check-In Response

- [ ] Get check-in token from email link
- [ ] Respond to check-in:
```bash
curl -X GET "https://YOUR_API_URL/check-in?token=CHECK_IN_TOKEN"
```
- [ ] Response is 200, success message
- [ ] DynamoDB shows `last_check_in` updated, `consecutive_missed_check_ins` reset to 0

---

## Summary

| # | Test | Result |
|---|------|--------|
| 1 | Create assignment — registered benefactor | ⬜ Pass / ⬜ Fail |
| 2 | Create assignment — unregistered (invitation) | ⬜ Pass / ⬜ Fail |
| 3 | Create assignment — time-delayed | ⬜ Pass / ⬜ Fail |
| 4 | Create assignment — multiple conditions | ⬜ Pass / ⬜ Fail |
| 5 | Duplicate assignment rejected | ⬜ Pass / ⬜ Fail |
| 6 | Validation errors (3 cases) | ⬜ Pass / ⬜ Fail |
| 7 | Get assignments | ⬜ Pass / ⬜ Fail |
| 8 | Benefactor accept | ⬜ Pass / ⬜ Fail |
| 9 | Benefactor decline | ⬜ Pass / ⬜ Fail |
| 10 | Validate access | ⬜ Pass / ⬜ Fail |
| 11 | Manual release | ⬜ Pass / ⬜ Fail |
| 12 | Update conditions | ⬜ Pass / ⬜ Fail |
| 13 | Revoke assignment | ⬜ Pass / ⬜ Fail |
| 14 | Delete pending assignment | ⬜ Pass / ⬜ Fail |
| 15 | Resend invitation | ⬜ Pass / ⬜ Fail |
| 16 | Scheduled jobs | ⬜ Pass / ⬜ Fail |
| 17 | Check-in response | ⬜ Pass / ⬜ Fail |

---

## Notes

_Use this space to record any failures, unexpected behavior, or follow-up items:_

