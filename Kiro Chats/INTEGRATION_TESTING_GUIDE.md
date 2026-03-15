# Integration Testing Guide: Legacy Maker Benefactor Assignment

This guide provides step-by-step instructions for manually testing all integration flows for the Legacy Maker Benefactor Assignment feature.

## Prerequisites

Before running these tests, ensure:
- [ ] SAM application is deployed to AWS
- [ ] DynamoDB tables are created (PersonaRelationshipsDB, AccessConditionsDB)
- [ ] Cognito User Pool is configured
- [ ] SES is configured for email sending (sandbox or production)
- [ ] EventBridge rules are enabled for scheduled jobs
- [ ] You have access to AWS Console for verification
- [ ] You have test user accounts (Legacy Maker and Benefactor)

## Test Environment Setup

### Required Test Accounts

1. **Legacy Maker Account**
   - Email: `legacy-maker-test@yourdomain.com`
   - Persona Type: `legacy_maker`
   - User ID: Record this for testing

2. **Benefactor Account (for existing user tests)**
   - Email: `benefactor-test@yourdomain.com`
   - Persona Type: `legacy_benefactor`
   - User ID: Record this for testing

3. **Unregistered Email (for invitation tests)**
   - Email: `new-benefactor-test@yourdomain.com`
   - Should NOT exist in Cognito User Pool

### API Endpoint URLs

Record your deployed API Gateway endpoints:
- Base URL: `https://[api-id].execute-api.[region].amazonaws.com/[stage]`
- Create Assignment: `POST /assignments`
- Get Assignments: `GET /assignments?userId={userId}`
- Update Assignment: `PUT /assignments`
- Accept/Decline: `POST /assignments/respond`
- Manual Release: `POST /assignments/manual-release`
- Resend Invitation: `POST /assignments/resend-invitation`
- Validate Access: `GET /validate-access?requestingUserId={id}&targetUserId={id}`
- Check-In Response: `GET /check-in?token={token}`

---

## Test 25.1: Assignment Creation Flow

**Requirements Tested:** 1.1, 1.3, 5.1, 6.2

### Objective
Verify that a Legacy Maker can create an assignment for an unregistered benefactor, invitation email is sent, and the assignment appears in the Legacy Maker's list.

### Steps

#### 1. Create Assignment for Unregistered Benefactor

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "new-benefactor-test@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "assignment_id": "uuid",
  "related_user_id": "pending_[uuid]",
  "invitation_sent": true,
  "message": "Assignment created successfully. Invitation email sent."
}
```

**Verification Checklist:**
- [ ] Response status code is 200
- [ ] Response contains `assignment_id`
- [ ] Response indicates `invitation_sent: true`
- [ ] No error messages in response

#### 2. Verify Invitation Email Sent

**Check:**
- [ ] Email received at `new-benefactor-test@yourdomain.com`
- [ ] Email contains assignment details
- [ ] Email contains registration link with invitation token
- [ ] Email explains access conditions (immediate access)
- [ ] Email is from correct sender address

**Email Content Should Include:**
- Legacy Maker's name
- Access conditions explanation
- Registration link: `https://[frontend-url]/register?token=[invitation-token]`
- Instructions for accepting/declining

#### 3. Verify Assignment in Legacy Maker's List

**API Call:**
```bash
curl -X GET "https://[your-api-url]/assignments?userId=[legacy-maker-id]" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]"
```

**Expected Response:**
```json
{
  "assignments": [
    {
      "initiator_id": "[legacy-maker-id]",
      "related_user_id": "pending_[uuid]",
      "benefactor_email": "new-benefactor-test@yourdomain.com",
      "account_status": "invitation_pending",
      "assignment_status": "pending",
      "access_conditions": [
        {
          "condition_type": "immediate",
          "status": "pending"
        }
      ],
      "created_at": "[timestamp]"
    }
  ]
}
```

**Verification Checklist:**
- [ ] Assignment appears in list
- [ ] `account_status` is "invitation_pending"
- [ ] `assignment_status` is "pending"
- [ ] `benefactor_email` matches
- [ ] Access conditions are correct

#### 4. Verify Database State

**DynamoDB - PersonaRelationshipsDB:**
```bash
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[legacy-maker-id]"}, "related_user_id": {"S": "pending_[uuid]"}}'
```

**Expected:**
- [ ] Record exists
- [ ] `status` is "pending"
- [ ] `created_via` is "maker_assignment"
- [ ] `relationship_type` is "maker_to_benefactor"

**DynamoDB - AccessConditionsDB:**
```bash
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "[legacy-maker-id]#pending_[uuid]"}}'
```

**Expected:**
- [ ] At least one condition record exists
- [ ] `condition_type` is "immediate"
- [ ] `status` is "pending"

**DynamoDB - PersonaSignupTempDB:**
```bash
aws dynamodb scan \
  --table-name PersonaSignupTempDB \
  --filter-expression "invitee_email = :email" \
  --expression-attribute-values '{":email": {"S": "new-benefactor-test@yourdomain.com"}}'
```

**Expected:**
- [ ] Invitation token record exists
- [ ] `invitee_email` matches
- [ ] `initiator_id` is legacy maker ID
- [ ] TTL is set (7 days from creation)

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---


## Test 25.2: Benefactor Registration and Acceptance Flow

**Requirements Tested:** 6.4, 6.5, 7.2, 7.4

### Objective
Verify that an invited benefactor can register using the invitation token, the assignment is automatically linked to their new account, they can accept the assignment, and the Legacy Maker receives confirmation.

### Steps

#### 1. Register with Invitation Token

**Frontend Action:**
- Navigate to registration link from invitation email
- Complete registration form with invitation token in URL
- Submit registration

**Backend (PostConfirmation Trigger):**
The Cognito PostConfirmation trigger should automatically:
- Validate invitation token
- Link new user to pending assignment
- Update assignment status to "awaiting_acceptance"
- Send assignment notification to new user

**Verification Checklist:**
- [ ] Registration completes successfully
- [ ] User receives welcome email
- [ ] User receives assignment notification email

#### 2. Verify Assignment Linked to New Account

**API Call (as Legacy Maker):**
```bash
curl -X GET "https://[your-api-url]/assignments?userId=[legacy-maker-id]" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]"
```

**Expected Changes:**
- [ ] `related_user_id` changed from "pending_[uuid]" to actual user ID
- [ ] `account_status` changed to "registered"
- [ ] `assignment_status` still "pending" (awaiting acceptance)

**DynamoDB Verification:**
```bash
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[legacy-maker-id]"}, "related_user_id": {"S": "[new-benefactor-id]"}}'
```

**Expected:**
- [ ] Record exists with real user ID (not pending_*)
- [ ] `status` is "pending"

#### 3. Accept Assignment as Benefactor

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/respond \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [benefactor-jwt-token]" \
  -d '{
    "action": "accept",
    "initiator_id": "[legacy-maker-id]"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Assignment accepted successfully"
}
```

**Verification Checklist:**
- [ ] Response status code is 200
- [ ] Response indicates success
- [ ] No error messages

#### 4. Verify Legacy Maker Receives Confirmation

**Check:**
- [ ] Email received at legacy maker's email address
- [ ] Email confirms benefactor accepted assignment
- [ ] Email includes benefactor's name
- [ ] Email timestamp is recent

#### 5. Verify Assignment Status Updated

**API Call (as Legacy Maker):**
```bash
curl -X GET "https://[your-api-url]/assignments?userId=[legacy-maker-id]" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]"
```

**Expected:**
- [ ] `assignment_status` is now "active"
- [ ] `account_status` is "registered"

**DynamoDB Verification:**
```bash
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[legacy-maker-id]"}, "related_user_id": {"S": "[benefactor-id]"}}'
```

**Expected:**
- [ ] `status` is "active"
- [ ] `updated_at` timestamp is recent

#### 6. Verify Access Granted (Immediate Access Condition)

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": true,
  "reason": "relationship_access"
}
```

**Verification Checklist:**
- [ ] `hasAccess` is true
- [ ] No unmet conditions listed

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---

## Test 25.3: Time-Delayed Access Flow

**Requirements Tested:** 2.3, 11.1, 11.4

### Objective
Verify that time-delayed access conditions prevent access before the activation date, and the TimeDelayProcessor scheduled job correctly activates access after the date passes.

### Steps

#### 1. Create Assignment with Future Activation Date

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "benefactor-test@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "time_delayed",
        "activation_date": "2026-02-22T12:00:00Z"
      }
    ]
  }'
```

**Note:** Use a date 1-2 hours in the future for testing.

**Verification Checklist:**
- [ ] Assignment created successfully
- [ ] Response contains assignment details
- [ ] Access condition includes activation_date

#### 2. Have Benefactor Accept Assignment

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/respond \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [benefactor-jwt-token]" \
  -d '{
    "action": "accept",
    "initiator_id": "[legacy-maker-id]"
  }'
```

**Verification:**
- [ ] Assignment accepted
- [ ] Status is "active"

#### 3. Verify Access Denied Before Activation Date

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": false,
  "reason": "conditions_not_met",
  "unmet_conditions": [
    {
      "condition_type": "time_delayed",
      "reason": "Activation date not reached",
      "activation_date": "2026-02-22T12:00:00Z"
    }
  ]
}
```

**Verification Checklist:**
- [ ] `hasAccess` is false
- [ ] Unmet conditions explain time delay
- [ ] Activation date is shown

#### 4. Simulate Time Passing (Update Database)

**For testing purposes, update the activation_date to the past:**

```bash
aws dynamodb update-item \
  --table-name AccessConditionsDB \
  --key '{"relationship_key": {"S": "[maker-id]#[benefactor-id]"}, "condition_id": {"S": "[condition-id]"}}' \
  --update-expression "SET activation_date = :date" \
  --expression-attribute-values '{":date": {"S": "2026-02-21T10:00:00Z"}}'
```

**Verification:**
- [ ] Database updated successfully
- [ ] activation_date is now in the past

#### 5. Run TimeDelayProcessor Manually

**Invoke Lambda:**
```bash
aws lambda invoke \
  --function-name TimeDelayProcessorFunction \
  --payload '{}' \
  response.json

cat response.json
```

**Expected Response:**
```json
{
  "statusCode": 200,
  "activations_processed": 1,
  "successful_activations": 1,
  "failed_activations": 0
}
```

**Verification Checklist:**
- [ ] Lambda executed successfully
- [ ] At least 1 activation processed
- [ ] No failures reported

#### 6. Verify Access Granted After Processing

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": true,
  "reason": "relationship_access"
}
```

**Verification Checklist:**
- [ ] `hasAccess` is now true
- [ ] No unmet conditions

#### 7. Verify Database State

**AccessConditionsDB:**
```bash
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "[maker-id]#[benefactor-id]"}}'
```

**Expected:**
- [ ] Condition `status` is "activated"
- [ ] `activated_at` timestamp is set

#### 8. Verify Benefactor Notification Email

**Check:**
- [ ] Email received at benefactor's email
- [ ] Email notifies that access is now granted
- [ ] Email includes Legacy Maker's name

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---


## Test 25.4: Inactivity Trigger Flow

**Requirements Tested:** 3.1, 3.2, 3.3, 11.2, 11.3

### Objective
Verify the complete inactivity monitoring flow: check-in emails are sent, responses reset the counter, missed check-ins trigger access activation.

### Steps

#### 1. Create Assignment with Inactivity Trigger

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "benefactor-test@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "inactivity_trigger",
        "inactivity_months": 1,
        "check_in_interval_days": 7
      }
    ]
  }'
```

**Verification:**
- [ ] Assignment created successfully
- [ ] Inactivity trigger configured

#### 2. Benefactor Accepts Assignment

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/respond \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [benefactor-jwt-token]" \
  -d '{
    "action": "accept",
    "initiator_id": "[legacy-maker-id]"
  }'
```

**Verification:**
- [ ] Assignment accepted
- [ ] Status is "active"

#### 3. Run CheckInSender Manually

**Invoke Lambda:**
```bash
aws lambda invoke \
  --function-name CheckInSenderFunction \
  --payload '{}' \
  response.json

cat response.json
```

**Expected Response:**
```json
{
  "statusCode": 200,
  "check_ins_sent": 1,
  "errors": 0
}
```

**Verification Checklist:**
- [ ] Lambda executed successfully
- [ ] At least 1 check-in sent

#### 4. Verify Check-In Email Sent

**Check Legacy Maker's Email:**
- [ ] Email received at legacy maker's email
- [ ] Email explains purpose of check-in
- [ ] Email contains unique verification link
- [ ] Link format: `https://[frontend-url]/check-in?token=[unique-token]`

**Email Content Should Include:**
- Explanation of inactivity monitoring
- Verification link
- Consequences of not responding
- Frequency of check-ins

#### 5. Respond to Check-In

**Click the verification link or make API call:**
```bash
curl -X GET "https://[your-api-url]/check-in?token=[check-in-token]"
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Check-in recorded successfully"
}
```

**Verification:**
- [ ] Response indicates success
- [ ] Success page displayed (if using browser)

#### 6. Verify Counter Reset

**DynamoDB Check:**
```bash
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "[maker-id]#[benefactor-id]"}}'
```

**Expected:**
- [ ] `last_check_in` timestamp is recent
- [ ] `consecutive_missed_check_ins` is 0

#### 7. Simulate Missed Check-Ins

**Update database to simulate missed check-ins:**

```bash
# Set last_check_in to 2 months ago
aws dynamodb update-item \
  --table-name AccessConditionsDB \
  --key '{"relationship_key": {"S": "[maker-id]#[benefactor-id]"}, "condition_id": {"S": "[condition-id]"}}' \
  --update-expression "SET last_check_in = :date, consecutive_missed_check_ins = :count" \
  --expression-attribute-values '{":date": {"S": "2025-12-21T10:00:00Z"}, ":count": {"N": "8"}}'
```

**Verification:**
- [ ] Database updated
- [ ] `last_check_in` is > inactivity_months ago
- [ ] `consecutive_missed_check_ins` is >= threshold

#### 8. Run InactivityProcessor Manually

**Invoke Lambda:**
```bash
aws lambda invoke \
  --function-name InactivityProcessorFunction \
  --payload '{}' \
  response.json

cat response.json
```

**Expected Response:**
```json
{
  "statusCode": 200,
  "activations_processed": 1,
  "successful_activations": 1,
  "failed_activations": 0
}
```

**Verification Checklist:**
- [ ] Lambda executed successfully
- [ ] At least 1 activation processed

#### 9. Verify Access Granted After Threshold

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": true,
  "reason": "relationship_access"
}
```

**Verification:**
- [ ] `hasAccess` is true
- [ ] Access granted due to inactivity

#### 10. Verify Benefactor Notification

**Check Benefactor's Email:**
- [ ] Email received notifying access granted
- [ ] Email explains inactivity trigger activated
- [ ] Email includes Legacy Maker's name

#### 11. Verify Database State

**AccessConditionsDB:**
```bash
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "[maker-id]#[benefactor-id]"}}'
```

**Expected:**
- [ ] Condition `status` is "activated"
- [ ] `activated_at` timestamp is set

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---

## Test 25.5: Manual Release Flow

**Requirements Tested:** 4.2, 4.3

### Objective
Verify that a Legacy Maker can manually release access, granting immediate access to benefactors, and notifications are sent.

### Steps

#### 1. Create Assignment with Manual Release

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "benefactor-test@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "manual_release"
      }
    ]
  }'
```

**Verification:**
- [ ] Assignment created successfully
- [ ] Manual release condition configured

#### 2. Benefactor Accepts Assignment

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/respond \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [benefactor-jwt-token]" \
  -d '{
    "action": "accept",
    "initiator_id": "[legacy-maker-id]"
  }'
```

**Verification:**
- [ ] Assignment accepted

#### 3. Verify Access Denied Before Release

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": false,
  "reason": "conditions_not_met",
  "unmet_conditions": [
    {
      "condition_type": "manual_release",
      "reason": "Awaiting manual release by Legacy Maker"
    }
  ]
}
```

**Verification:**
- [ ] `hasAccess` is false
- [ ] Manual release condition shown as unmet

#### 4. Trigger Manual Release

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/manual-release \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{}'
```

**Expected Response:**
```json
{
  "success": true,
  "releases_processed": 1,
  "message": "Manual release completed successfully"
}
```

**Verification Checklist:**
- [ ] Response status code is 200
- [ ] Response indicates success
- [ ] At least 1 release processed

#### 5. Verify Access Granted Immediately

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": true,
  "reason": "relationship_access"
}
```

**Verification:**
- [ ] `hasAccess` is now true
- [ ] No unmet conditions

#### 6. Verify Benefactor Notification Sent

**Check Benefactor's Email:**
- [ ] Email received notifying access granted
- [ ] Email explains manual release was triggered
- [ ] Email includes Legacy Maker's name
- [ ] Email timestamp is recent

#### 7. Verify Database State

**AccessConditionsDB:**
```bash
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "[maker-id]#[benefactor-id]"}}'
```

**Expected:**
- [ ] Condition `status` is "activated"
- [ ] `released_at` timestamp is set
- [ ] `released_by` is legacy maker's user ID

#### 8. Test Idempotence - Trigger Release Again

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/manual-release \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{}'
```

**Expected Response:**
```json
{
  "success": true,
  "releases_processed": 0,
  "message": "No pending manual releases found"
}
```

**Verification:**
- [ ] No duplicate processing
- [ ] No duplicate emails sent
- [ ] Response indicates already released

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---


## Test 25.6: Assignment Management Flows

**Requirements Tested:** 5.3, 5.5, 5.7, 5.10, 5.11

### Objective
Verify that Legacy Makers can edit pending assignments, revoke active assignments (with immediate access denial), delete pending assignments, and resend invitations.

### Steps

#### Part A: Edit Pending Assignment Conditions

##### 1. Create Pending Assignment

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "benefactor-test@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Verification:**
- [ ] Assignment created
- [ ] Status is "pending"

##### 2. Edit Access Conditions

**API Call:**
```bash
curl -X PUT https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "action": "update_conditions",
    "related_user_id": "[benefactor-id]",
    "access_conditions": [
      {
        "condition_type": "time_delayed",
        "activation_date": "2026-03-01T12:00:00Z"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Access conditions updated successfully"
}
```

**Verification Checklist:**
- [ ] Response indicates success
- [ ] No errors

##### 3. Verify Conditions Updated

**API Call:**
```bash
curl -X GET "https://[your-api-url]/assignments?userId=[legacy-maker-id]" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]"
```

**Expected:**
- [ ] Assignment shows new access conditions
- [ ] Old conditions removed
- [ ] New time_delayed condition present

##### 4. Verify Cannot Edit Active Assignment

**First, accept the assignment:**
```bash
curl -X POST https://[your-api-url]/assignments/respond \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [benefactor-jwt-token]" \
  -d '{
    "action": "accept",
    "initiator_id": "[legacy-maker-id]"
  }'
```

**Then try to edit:**
```bash
curl -X PUT https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "action": "update_conditions",
    "related_user_id": "[benefactor-id]",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "error": "Cannot edit active assignment",
  "message": "Only pending assignments can be edited"
}
```

**Verification:**
- [ ] Edit rejected
- [ ] Error message explains restriction

---

#### Part B: Revoke Active Assignment

##### 1. Verify Access Before Revocation

**API Call:**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected:**
- [ ] `hasAccess` is true (assuming conditions met)

##### 2. Revoke Assignment

**API Call:**
```bash
curl -X PUT https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "action": "revoke",
    "related_user_id": "[benefactor-id]"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Assignment revoked successfully"
}
```

**Verification:**
- [ ] Response indicates success

##### 3. Verify Access Immediately Denied

**API Call (immediately after revocation):**
```bash
curl -X GET "https://[your-api-url]/validate-access?requestingUserId=[benefactor-id]&targetUserId=[legacy-maker-id]" \
  -H "Authorization: Bearer [benefactor-jwt-token]"
```

**Expected Response:**
```json
{
  "hasAccess": false,
  "reason": "no_relationship"
}
```

**Verification:**
- [ ] `hasAccess` is false
- [ ] Access denied immediately

##### 4. Verify Benefactor Notification

**Check Benefactor's Email:**
- [ ] Email received notifying revocation
- [ ] Email explains assignment was revoked
- [ ] Email includes Legacy Maker's name

##### 5. Verify Database State

**PersonaRelationshipsDB:**
```bash
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[legacy-maker-id]"}, "related_user_id": {"S": "[benefactor-id]"}}'
```

**Expected:**
- [ ] `status` is "revoked"
- [ ] `updated_at` timestamp is recent

---

#### Part C: Delete Pending Assignment

##### 1. Create New Pending Assignment

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "another-benefactor@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Verification:**
- [ ] Assignment created
- [ ] Status is "pending"

##### 2. Delete Pending Assignment

**API Call:**
```bash
curl -X PUT https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "action": "delete",
    "related_user_id": "[benefactor-id]"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Assignment deleted successfully"
}
```

**Verification:**
- [ ] Response indicates success

##### 3. Verify Assignment Removed

**API Call:**
```bash
curl -X GET "https://[your-api-url]/assignments?userId=[legacy-maker-id]" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]"
```

**Expected:**
- [ ] Deleted assignment not in list

**DynamoDB Verification:**
```bash
aws dynamodb get-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[legacy-maker-id]"}, "related_user_id": {"S": "[benefactor-id]"}}'
```

**Expected:**
- [ ] Record does not exist

##### 4. Verify Cannot Delete Active Assignment

**Try to delete an active assignment:**
```bash
curl -X PUT https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "action": "delete",
    "related_user_id": "[active-benefactor-id]"
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "error": "Cannot delete active assignment",
  "message": "Only pending assignments can be deleted. Use revoke for active assignments."
}
```

**Verification:**
- [ ] Delete rejected
- [ ] Error message explains restriction

---

#### Part D: Resend Invitation

##### 1. Create Assignment for Unregistered Benefactor

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "unregistered-benefactor@yourdomain.com",
    "access_conditions": [
      {
        "condition_type": "immediate"
      }
    ]
  }'
```

**Verification:**
- [ ] Assignment created
- [ ] Invitation sent

##### 2. Wait or Simulate Token Expiration

**For testing, you can:**
- Wait 7 days for natural expiration, OR
- Manually delete the token from PersonaSignupTempDB

##### 3. Resend Invitation

**API Call:**
```bash
curl -X POST https://[your-api-url]/assignments/resend-invitation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "unregistered-benefactor@yourdomain.com"
  }'
```

**Expected Response:**
```json
{
  "success": true,
  "message": "Invitation resent successfully"
}
```

**Verification:**
- [ ] Response indicates success

##### 4. Verify New Invitation Email Sent

**Check Email:**
- [ ] New invitation email received
- [ ] Email contains new invitation token
- [ ] Email has recent timestamp

##### 5. Verify New Token in Database

**PersonaSignupTempDB:**
```bash
aws dynamodb scan \
  --table-name PersonaSignupTempDB \
  --filter-expression "invitee_email = :email" \
  --expression-attribute-values '{":email": {"S": "unregistered-benefactor@yourdomain.com"}}'
```

**Expected:**
- [ ] New token record exists
- [ ] TTL is reset (7 days from now)

##### 6. Verify Cannot Resend for Registered Benefactor

**Try to resend for registered user:**
```bash
curl -X POST https://[your-api-url]/assignments/resend-invitation \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [legacy-maker-jwt-token]" \
  -d '{
    "benefactor_email": "benefactor-test@yourdomain.com"
  }'
```

**Expected Response:**
```json
{
  "success": false,
  "error": "Benefactor already registered",
  "message": "Cannot resend invitation for registered users"
}
```

**Verification:**
- [ ] Resend rejected
- [ ] Error message explains restriction

### Test Result
- [ ] **PASS** - All verifications successful
- [ ] **FAIL** - Document failures:

---

## Summary and Sign-Off

### Test Execution Summary

| Test | Status | Notes |
|------|--------|-------|
| 25.1 - Assignment Creation | ☐ PASS ☐ FAIL | |
| 25.2 - Registration & Acceptance | ☐ PASS ☐ FAIL | |
| 25.3 - Time-Delayed Access | ☐ PASS ☐ FAIL | |
| 25.4 - Inactivity Trigger | ☐ PASS ☐ FAIL | |
| 25.5 - Manual Release | ☐ PASS ☐ FAIL | |
| 25.6 - Assignment Management | ☐ PASS ☐ FAIL | |

### Overall Result

- [ ] **ALL TESTS PASSED** - Feature is ready for production
- [ ] **SOME TESTS FAILED** - Review failures and fix issues

### Issues Found

Document any issues discovered during testing:

1. 
2. 
3. 

### Recommendations

Based on testing results:

1. 
2. 
3. 

### Sign-Off

- Tester Name: ___________________
- Date: ___________________
- Signature: ___________________

---

## Appendix: Useful Commands

### Check CloudWatch Logs

```bash
# View Lambda function logs
aws logs tail /aws/lambda/[FunctionName] --follow

# View specific log group
aws logs tail /aws/lambda/CreateAssignmentFunction --since 1h
```

### Query DynamoDB Tables

```bash
# Scan PersonaRelationshipsDB
aws dynamodb scan --table-name PersonaRelationshipsDB --max-items 10

# Scan AccessConditionsDB
aws dynamodb scan --table-name AccessConditionsDB --max-items 10

# Query by relationship key
aws dynamodb query \
  --table-name AccessConditionsDB \
  --key-condition-expression "relationship_key = :rk" \
  --expression-attribute-values '{":rk": {"S": "maker-id#benefactor-id"}}'
```

### Check EventBridge Rules

```bash
# List rules
aws events list-rules

# Check rule status
aws events describe-rule --name TimeDelayProcessorRule

# Manually trigger rule
aws events put-events --entries '[{"Source":"manual.test","DetailType":"test","Detail":"{}"}]'
```

### Check SES Email Sending

```bash
# Check sending statistics
aws ses get-send-statistics

# Check email identity verification
aws ses get-identity-verification-attributes --identities your-email@domain.com
```

### Clean Up Test Data

```bash
# Delete test relationship
aws dynamodb delete-item \
  --table-name PersonaRelationshipsDB \
  --key '{"initiator_id": {"S": "[maker-id]"}, "related_user_id": {"S": "[benefactor-id]"}}'

# Delete test access conditions
aws dynamodb delete-item \
  --table-name AccessConditionsDB \
  --key '{"relationship_key": {"S": "[maker-id]#[benefactor-id]"}, "condition_id": {"S": "[condition-id]"}}'
```

