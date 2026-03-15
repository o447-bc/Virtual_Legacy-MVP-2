# Data Format Audit - Frontend to Lambda Communication

## Summary: All Services Use JSON ✅

**Result:** No Lambda functions use FormData/Blob. All use JSON.

---

## Frontend Services

### 1. videoService.ts ✅ JSON
**Endpoint:** `/functions/videoFunctions/upload`  
**Method:** POST  
**Format:** JSON with base64-encoded video

```typescript
// Converts Blob to base64
const base64Video = await new Promise<string>((resolve, reject) => {
  const reader = new FileReader();
  reader.onloadend = () => {
    const base64 = reader.result as string;
    resolve(base64.split(',')[1]); // Remove data:video/webm;base64, prefix
  };
  reader.onerror = reject;
  reader.readAsDataURL(videoData.videoBlob);
});

// Sends as JSON
fetch(url, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${idToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    questionId: videoData.questionId,
    questionType: videoData.questionType,
    questionText: videoData.questionText,
    videoData: base64Video  // base64 string
  })
});
```

**Lambda:** `uploadVideoResponse/app.py`
```python
body = json.loads(event['body'])
video_data = body.get('videoData')  # base64 string
question_id = body.get('questionId')
question_type = body.get('questionType')
question_text = body.get('questionText')
```

---

### 2. inviteService.ts ✅ JSON
**Endpoint:** `/invites/send`  
**Method:** POST  
**Format:** JSON

```typescript
fetch(url, {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${idToken}`
  },
  body: JSON.stringify({
    benefactor_email: '...',
    invitee_email: '...'
  })
});
```

**Lambda:** `sendInviteEmail/app.py`
```python
body = json.loads(event['body'])
```

---

### 3. relationshipService.ts ✅ JSON
**Endpoint:** `/relationships`  
**Method:** GET  
**Format:** Query parameters (no body)

```typescript
fetch(`${url}?userId=${userId}`, {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${idToken}`
  }
});
```

**Lambda:** `getRelationships/app.py`
```python
# No body parsing needed for GET requests
```

---

### 4. getMakerVideos ✅ JSON Response
**Endpoint:** `/videos/{makerId}`  
**Method:** GET  
**Format:** No body (GET request)

```typescript
fetch(url, {
  headers: { 'Authorization': `Bearer ${idToken}` }
});
```

**Lambda:** `getMakerVideos/app.py`
```python
# Returns JSON response
return {
  'statusCode': 200,
  'headers': {'Access-Control-Allow-Origin': '*'},
  'body': json.dumps(grouped, cls=DecimalEncoder)
}
```

---

## All Lambda Functions Checked

### Functions that parse request body:
1. ✅ `uploadVideoResponse/app.py` - Uses `json.loads(event['body'])`
2. ✅ `incrementUserLevel/app.py` - Uses `json.loads(event['body'])`
3. ✅ `incrementUserLevel2/app.py` - Uses `json.loads(event['body'])`
4. ✅ `sendInviteEmail/app.py` - Uses `json.loads(event['body'])`

### Functions that don't parse body (GET requests):
1. ✅ `getMakerVideos/app.py` - GET request, no body
2. ✅ `getRelationships/app.py` - GET request, no body
3. ✅ `getProgressSummary/app.py` - GET request, no body
4. ✅ `getProgressSummary2/app.py` - GET request, no body
5. ✅ `getQuestionTypes/app.py` - GET request, no body
6. ✅ `getQuestionById/app.py` - GET request, no body
7. ✅ `getUnansweredQuestions/app.py` - GET request, no body

---

## Conclusion

✅ **All frontend services send JSON**  
✅ **All Lambda functions expect JSON**  
✅ **No FormData or multipart/form-data is used anywhere**  
✅ **Video uploads use base64-encoded strings in JSON**

**No changes needed.** The system is consistent.

---

## Historical Note

Previously, `videoService.ts` was sending FormData with a Blob, which caused the 500 error because the Lambda expected JSON with base64. This was fixed by:

1. Converting Blob to base64 using FileReader
2. Sending as JSON with `Content-Type: application/json`
3. Matching the Lambda's expected format

This is now documented in `LAMBDA_MODIFICATION_RULES.md` to prevent future issues.
