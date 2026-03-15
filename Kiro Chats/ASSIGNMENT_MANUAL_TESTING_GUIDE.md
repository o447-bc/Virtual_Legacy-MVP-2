# Manual Testing Guide: Assignment Creation and Retrieval

This guide walks through manual testing of the CreateAssignment and GetAssignments Lambda functions to verify they work correctly.

## Prerequisites

1. **AWS SAM CLI** installed and configured
2. **DynamoDB tables** deployed:
   - PersonaRelationshipsDB
   - AccessConditionsDB
   - PersonaSignupTempDB
3. **Cognito User Pool** configured with at least one test user
4. **Valid JWT token** from a Legacy Maker user

## Test Setup

### 1. Get a Valid JWT Token

First, you need a JWT token from a Legacy Maker user. You can get this by:

```bash
# Option 1: Login through the frontend and copy the token from browser dev tools
# Option 2: Use AWS CLI to authenticate
aws cognito-idp initiate-auth \
  --auth-flow USER_PASSWORD_AUTH \
  --client-id YOUR_CLIENT_ID \
  --auth-parameters USERNAME=test@example.com,PASSWORD=YourPassword
```

Save the `IdToken` from the response - this is your JWT token.

### 2. Extract User ID from Token

You can decode the JWT token to see the user ID (sub claim):

```bash
# Decode JWT payload (middle section between dots)
echo "YOUR_JWT_TOKEN" | cut -d'.' -f2 | base64 -d | jq
```

Look for the `sub` field - this is your Legacy Maker's user ID.

## Test Scenarios

### Test 1: Create Assignment with Immediate Access (Registered Benefactor)

**Purpose**: Verify assignment creation for a benefactor who already has an account.

**Prerequisites**:
- Have a registered benefactor email in Cognito
- Have a valid Legacy Maker JWT token

**Test Request**:

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "registered-benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Expected Response** (200 OK):
```json
{
  "message": "Assignment created successfully",
  "assignment_id": "maker-user-id#benefactor-user-id",
  "status": "pending",
  "benefactor_registered": true,
  "invitation_sent": true,
  "invitation_token": null,
  "conditions_created": 1
}
```

**Verification Steps**:
1. Check PersonaRelationshipsDB for new record with:
   - `initiator_id` = Legacy Maker's user ID
   - `related_user_id` = Benefactor's user ID
   - `status` = "pending"
   - `created_via` = "maker_assignment"

2. Check AccessConditionsDB for new record with:
   - `relationship_key` = "maker-id#benefactor-id"
   - `condition_type` = "immediate"
   - `status` = "pending"

3. Check benefactor's email for notification

**DynamoDB Query to Verify**:
```bash
# Check PersonaRelationshipsDB
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "MAKER_USER_ID"}, "related_user_id": {"S": "BENEFACTOR_USER_ID"}}'

# Check AccessConditionsDB
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rkey" \
  --expression-attribute-values '{":rkey": {"S": "MAKER_USER_ID#BENEFACTOR_USER_ID"}}'
```

---

### Test 2: Create Assignment with Time-Delayed Access (Unregistered Benefactor)

**Purpose**: Verify assignment creation for a benefactor who doesn't have an account yet.

**Test Request**:

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "new-benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "time_delayed",
        "activation_date": "2026-12-31T23:59:59Z"
      }
    ]
  }'
```

**Expected Response** (200 OK):
```json
{
  "message": "Assignment created successfully",
  "assignment_id": "maker-user-id#pending#new-benefactor@example.com",
  "status": "pending",
  "benefactor_registered": false,
  "invitation_sent": true,
  "invitation_token": "uuid-token-here",
  "conditions_created": 1
}
```

**Verification Steps**:
1. Check PersonaRelationshipsDB for new record with:
   - `initiator_id` = Legacy Maker's user ID
   - `related_user_id` = "pending#new-benefactor@example.com"
   - `status` = "pending"

2. Check AccessConditionsDB for new record with:
   - `condition_type` = "time_delayed"
   - `activation_date` = "2026-12-31T23:59:59Z"

3. Check PersonaSignupTempDB for invitation token:
   - `userName` = invitation token UUID
   - `benefactor_email` = "new-benefactor@example.com"
   - `invite_type` = "maker_assignment"

4. Check email for invitation with registration link

**DynamoDB Query to Verify**:
```bash
# Check invitation token
aws dynamodb get-item \
  --table-name PersonaSignupTempDB \
  --key '{"userName": {"S": "INVITATION_TOKEN_UUID"}}'
```

---

### Test 3: Create Assignment with Multiple Access Conditions

**Purpose**: Verify that multiple access conditions can be created for a single assignment.

**Test Request**:

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "time_delayed",
        "activation_date": "2026-06-01T00:00:00Z"
      },
      {
        "condition_type": "inactivity_trigger",
        "inactivity_months": 12,
        "check_in_interval_days": 30
      },
      {
        "condition_type": "manual_release"
      }
    ]
  }'
```

**Expected Response** (200 OK):
```json
{
  "message": "Assignment created successfully",
  "assignment_id": "maker-user-id#benefactor-user-id",
  "status": "pending",
  "benefactor_registered": true,
  "invitation_sent": true,
  "invitation_token": null,
  "conditions_created": 3
}
```

**Verification Steps**:
1. Check AccessConditionsDB - should have 3 records with same `relationship_key`
2. Each condition should have correct type-specific fields

---

### Test 4: Attempt Duplicate Assignment (Should Fail)

**Purpose**: Verify that duplicate assignments are prevented.

**Test Request**:

```bash
# First, create an assignment (use Test 1 request)
# Then, try to create the same assignment again:

curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "registered-benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Expected Response** (409 Conflict):
```json
{
  "error": "Assignment already exists for this benefactor",
  "existing_status": "pending"
}
```

---

### Test 5: Invalid Access Conditions (Should Fail)

**Purpose**: Verify validation of access conditions.

**Test 5a: Past Date for Time-Delayed**

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "time_delayed",
        "activation_date": "2020-01-01T00:00:00Z"
      }
    ]
  }'
```

**Expected Response** (400 Bad Request):
```json
{
  "error": "Time-delayed condition at index 0: Activation date must be in the future..."
}
```

**Test 5b: Invalid Inactivity Months**

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "benefactor@example.com",
    "access_conditions": [
      {
        "condition_type": "inactivity_trigger",
        "inactivity_months": 30
      }
    ]
  }'
```

**Expected Response** (400 Bad Request):
```json
{
  "error": "Inactivity trigger condition at index 0: Inactivity months cannot exceed 24 months"
}
```

**Test 5c: No Access Conditions**

```bash
curl -X POST https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "benefactor_email": "benefactor@example.com",
    "access_conditions": []
  }'
```

**Expected Response** (400 Bad Request):
```json
{
  "error": "At least one access condition is required"
}
```

---

### Test 6: Get Assignments for Legacy Maker

**Purpose**: Verify retrieval of all assignments for a Legacy Maker.

**Prerequisites**:
- Have created at least one assignment (from previous tests)

**Test Request**:

```bash
curl -X GET https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Response** (200 OK):
```json
{
  "assignments": [
    {
      "initiator_id": "maker-user-id",
      "related_user_id": "benefactor-user-id",
      "benefactor_email": "benefactor@example.com",
      "benefactor_first_name": "John",
      "benefactor_last_name": "Doe",
      "account_status": "registered",
      "assignment_status": "pending",
      "relationship_type": "maker_to_benefactor",
      "created_at": "2026-02-21T10:00:00Z",
      "updated_at": "2026-02-21T10:00:00Z",
      "access_conditions": [
        {
          "condition_id": "uuid",
          "condition_type": "immediate",
          "status": "pending"
        }
      ]
    },
    {
      "initiator_id": "maker-user-id",
      "related_user_id": "pending#new-benefactor@example.com",
      "benefactor_email": "new-benefactor@example.com",
      "benefactor_first_name": null,
      "benefactor_last_name": null,
      "account_status": "invitation_pending",
      "assignment_status": "pending",
      "relationship_type": "maker_to_benefactor",
      "created_at": "2026-02-21T10:05:00Z",
      "updated_at": "2026-02-21T10:05:00Z",
      "access_conditions": [
        {
          "condition_id": "uuid",
          "condition_type": "time_delayed",
          "status": "pending",
          "activation_date": "2026-12-31T23:59:59Z"
        }
      ]
    }
  ],
  "count": 2
}
```

**Verification Steps**:
1. Verify all assignments are returned
2. Check that `account_status` is correct:
   - "registered" for existing users
   - "invitation_pending" for unregistered users
3. Verify access conditions are included for each assignment
4. Check that benefactor details are populated correctly

---

### Test 7: Get Assignments with No Assignments

**Purpose**: Verify behavior when Legacy Maker has no assignments.

**Prerequisites**:
- Use a Legacy Maker who hasn't created any assignments

**Test Request**:

```bash
curl -X GET https://YOUR_API_GATEWAY_URL/assignments \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

**Expected Response** (200 OK):
```json
{
  "assignments": [],
  "count": 0
}
```

---

## Testing with Local SAM

If you want to test locally before deploying:

### 1. Start SAM Local API

```bash
cd SamLambda
sam local start-api --env-vars env.json
```

### 2. Create env.json with Environment Variables

```json
{
  "CreateAssignmentFunction": {
    "USER_POOL_ID": "your-user-pool-id",
    "SENDER_EMAIL": "noreply@virtuallegacy.com"
  },
  "GetAssignmentsFunction": {
    "USER_POOL_ID": "your-user-pool-id"
  }
}
```

### 3. Test Against Local Endpoint

Replace `https://YOUR_API_GATEWAY_URL` with `http://localhost:3000` in all curl commands.

---

## Common Issues and Troubleshooting

### Issue 1: 401 Unauthorized

**Cause**: Invalid or expired JWT token

**Solution**: 
- Get a fresh JWT token from Cognito
- Verify the token is in the format: `Bearer YOUR_TOKEN`
- Check that the user is a Legacy Maker (persona_type)

### Issue 2: 500 Internal Server Error

**Cause**: Missing environment variables or DynamoDB tables

**Solution**:
- Check CloudWatch logs for the Lambda function
- Verify all DynamoDB tables exist
- Verify USER_POOL_ID environment variable is set
- Check IAM permissions for Lambda function

### Issue 3: Email Not Sent

**Cause**: SES not configured or email not verified

**Solution**:
- Verify sender email in SES
- Check SES is out of sandbox mode (or verify recipient emails)
- Check CloudWatch logs for SES errors

### Issue 4: Cognito User Not Found

**Cause**: Email doesn't exist in user pool

**Solution**:
- This is expected behavior for unregistered users
- Verify invitation flow is triggered (check PersonaSignupTempDB)

---

## Success Criteria

✅ **Test 1**: Assignment created for registered benefactor with immediate access
✅ **Test 2**: Assignment created for unregistered benefactor with invitation token
✅ **Test 3**: Multiple access conditions created successfully
✅ **Test 4**: Duplicate assignment prevented (409 error)
✅ **Test 5**: Invalid access conditions rejected (400 errors)
✅ **Test 6**: All assignments retrieved correctly with enriched data
✅ **Test 7**: Empty assignments list returned when no assignments exist

All validation tests pass (22/22) ✅

---

## Next Steps

After verifying these tests pass:

1. ✅ Mark Task 5 (Checkpoint) as complete
2. ➡️ Proceed to Task 6: Implement UpdateAssignment Lambda function
3. ➡️ Continue with remaining tasks in the implementation plan

---

## Notes

- All timestamps should be in ISO 8601 format with UTC timezone
- JWT tokens expire after a certain time (typically 1 hour)
- DynamoDB queries may have eventual consistency - allow a few seconds for data to propagate
- Email delivery may take a few seconds - check spam folder if not received
