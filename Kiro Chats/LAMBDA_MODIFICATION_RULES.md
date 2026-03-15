# Lambda Modification Rules

## CRITICAL: Always Follow These Steps Before Modifying Lambda Functions

### Rule 1: Verify Frontend-Lambda Data Contract

**BEFORE modifying any Lambda function that receives data from the frontend:**

1. **Check the frontend code** to see HOW data is sent:
   - Look in `FrontEndCode/src/services/` for the service that calls the Lambda
   - Check if it sends `FormData` (multipart) or `JSON`
   - Check if video/file data is sent as `Blob` or `base64`

2. **Check the Lambda code** to see HOW it expects data:
   - Look for `json.loads(event['body'])` = expects JSON
   - Look for multipart parsing = expects FormData
   - Look for `base64.b64decode()` = expects base64-encoded data

3. **Verify they match** - Frontend send format MUST match Lambda receive format

### Rule 2: Video Upload Specific Rules

**The uploadVideoResponse Lambda expects:**
```python
body = json.loads(event['body'])  # JSON format
video_data = body.get('videoData')  # Base64-encoded video string
question_id = body.get('questionId')
question_type = body.get('questionType')
question_text = body.get('questionText')
```

**The frontend MUST send:**
```typescript
// Convert blob to base64
const base64Video = await new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result as string;
    resolve(base64.split(',')[1]); // Remove data:video/webm;base64, prefix
  };
  reader.onerror = reject;
  reader.readAsDataURL(videoBlob);
});

// Send as JSON
fetch(url, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`,
    'Content-Type': 'application/json'  // CRITICAL: JSON, not multipart
  },
  body: JSON.stringify({
    questionId: '...',
    questionType: '...',
    questionText: '...',
    videoData: base64Video  // CRITICAL: base64 string, not Blob
  })
});
```

### Rule 3: Test After Lambda Modifications

**ALWAYS test these after modifying a Lambda:**

1. **Test the actual functionality** - Don't just deploy and assume it works
2. **Check CloudWatch logs** if there's an error:
   ```bash
   # Find the actual Lambda function name
   aws lambda list-functions --query 'Functions[?contains(FunctionName, `YourFunction`)].FunctionName'
   
   # Check logs
   aws logs tail /aws/lambda/ACTUAL-FUNCTION-NAME --since 10m --format short
   ```
3. **Check browser console** for frontend errors
4. **Verify the full flow** - Record a video, submit it, check it appears in the viewer

### Rule 4: When Adding New Fields to Lambda Functions

**If adding a new field to a Lambda function (like we did with `questionText`):**

1. **Extract the field from the request:**
   ```python
   question_text = body.get('questionText', '')  # Use default if missing
   ```

2. **Pass it to all functions that need it:**
   ```python
   # Update function signature
   def update_user_question_status(user_id, question_id, question_type, filename, s3_key, question_text):
   
   # Update function call
   update_user_question_status(user_id, question_id, question_type, filename, s3_key, question_text)
   ```

3. **Add it to the database operation:**
   ```python
   table.put_item(
       Item={
           'userId': user_id,
           'questionId': question_id,
           'Question': question_text  # New field
       }
   )
   ```

4. **Verify the frontend sends it:**
   - Check `videoService.ts` or relevant service file
   - Ensure the field is included in the request body

### Rule 5: CORS Headers

**When modifying Lambda functions, NEVER change CORS headers unless explicitly required.**

Copy CORS headers exactly from a working Lambda like `incrementUserLevel2/app.py`:

```python
# OPTIONS request
if event.get('httpMethod') == 'OPTIONS':
    return {
        'statusCode': 200,
        'headers': {
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
            'Access-Control-Allow-Methods': 'POST,OPTIONS'
        },
        'body': ''
    }

# All other responses
return {
    'statusCode': 200,  # or 400, 401, 500, etc.
    'headers': {'Access-Control-Allow-Origin': '*'},
    'body': json.dumps(response_data)
}
```

### Quick Checklist Before Modifying Lambda

- [ ] Checked how frontend sends data (FormData vs JSON, Blob vs base64)
- [ ] Checked how Lambda expects data (json.loads vs multipart parsing)
- [ ] Verified data formats match
- [ ] Updated all function signatures if adding parameters
- [ ] Updated all function calls with new parameters
- [ ] Tested the actual functionality after deployment
- [ ] Checked CloudWatch logs for errors
- [ ] Verified CORS headers are correct

### Common Mistakes to Avoid

❌ **DON'T:**
- Assume the Lambda expects FormData just because it's a file upload
- Modify Lambda without checking the frontend code
- Deploy without testing
- Change CORS headers unnecessarily

✅ **DO:**
- Always verify the data contract between frontend and Lambda
- Test after every Lambda modification
- Check CloudWatch logs if something breaks
- Keep CORS headers consistent across all Lambdas

---

## Instructions to Give AI Assistant

When asking an AI assistant to modify Lambda functions, provide these instructions:

```
CRITICAL LAMBDA MODIFICATION RULES:

1. Before modifying any Lambda function, you MUST:
   - Read the frontend service file that calls this Lambda
   - Verify how data is sent (FormData vs JSON, Blob vs base64)
   - Verify the Lambda expects the same format
   - If they don't match, fix the mismatch

2. For video upload Lambda (uploadVideoResponse):
   - Lambda expects JSON with base64-encoded video
   - Frontend must send JSON, NOT FormData
   - Video must be base64 string, NOT Blob

3. After modifying Lambda:
   - Deploy with: sam build && sam deploy --no-confirm-changeset
   - Test the actual functionality
   - Check CloudWatch logs if errors occur
   - Verify browser console for frontend errors

4. Never change CORS headers unless explicitly required
   - Copy from incrementUserLevel2/app.py if needed

5. When adding new fields:
   - Extract from request body
   - Update all function signatures
   - Update all function calls
   - Add to database operations
   - Verify frontend sends the field

See LAMBDA_MODIFICATION_RULES.md for full details.
```
