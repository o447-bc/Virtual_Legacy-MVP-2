# Credential Rotation Guide
## Rotating Cognito App Client After GitHub Exposure

**Why:** Your Cognito Client ID was in GitHub history and should be rotated as a security best practice.

**Risk Level:** Medium - Someone could attempt to use your Client ID for authentication attempts.

**Time Required:** 10-15 minutes

---

## Step 1: Create New Cognito App Client

### Via AWS Console:

1. **Go to Cognito**
   - Open AWS Console
   - Navigate to Amazon Cognito
   - Select "User pools"

2. **Select Your User Pool**
   - Click on pool: `us-east-1_KsG65yYlo`

3. **Create New App Client**
   - Go to "App integration" tab
   - Scroll to "App clients and analytics"
   - Click "Create app client"

4. **Configure New Client**
   ```
   App client name: virtual-legacy-web-client-v2
   
   Authentication flows:
   ✅ ALLOW_USER_PASSWORD_AUTH
   ✅ ALLOW_REFRESH_TOKEN_AUTH
   ✅ ALLOW_USER_SRP_AUTH
   
   Token expiration:
   - Access token: 60 minutes (default)
   - ID token: 60 minutes (default)
   - Refresh token: 30 days (default)
   
   ❌ Generate client secret: NO (for web apps)
   ```

5. **Save and Copy Client ID**
   - Click "Create app client"
   - Copy the new Client ID (looks like: `abc123xyz456def789`)

### Via AWS CLI (Alternative):

```bash
aws cognito-idp create-user-pool-client \
  --user-pool-id us-east-1_KsG65yYlo \
  --client-name virtual-legacy-web-client-v2 \
  --explicit-auth-flows ALLOW_USER_PASSWORD_AUTH ALLOW_REFRESH_TOKEN_AUTH ALLOW_USER_SRP_AUTH \
  --generate-secret false \
  --region us-east-1
```

---

## Step 2: Update Your .env File

```bash
# Edit FrontEndCode/.env
nano FrontEndCode/.env

# Change this line:
VITE_USER_POOL_CLIENT_ID=gcj7ke19nrev9gjmvg564rv6j

# To your new Client ID:
VITE_USER_POOL_CLIENT_ID=your-new-client-id-here
```

---

## Step 3: Test the Application

```bash
cd FrontEndCode
npm run dev
```

**Test these features:**
- ✅ Login with existing user
- ✅ Signup new user
- ✅ Password reset
- ✅ All authenticated features

**If everything works:** Proceed to Step 4

**If login fails:** 
- Check that new Client ID is correct in .env
- Verify authentication flows are enabled in Cognito
- Check browser console for errors

---

## Step 4: Delete Old App Client

**⚠️ ONLY do this after confirming new client works!**

1. Go to Cognito → Your User Pool → App integration
2. Find old app client: `gcj7ke19nrev9gjmvg564rv6j`
3. Click "Delete"
4. Confirm deletion

This invalidates the old Client ID that was in GitHub.

---

## Step 5: Update Production Deployment

If you have a production deployment:

### AWS Amplify:
1. Go to Amplify Console
2. Select your app
3. Environment variables
4. Update `VITE_USER_POOL_CLIENT_ID` with new value
5. Redeploy

### Other Hosting (Vercel, Netlify, etc.):
1. Go to your hosting dashboard
2. Update environment variable
3. Trigger new deployment

---

## Step 6: Update Team Members

If other developers are working on this:

1. **Don't commit .env to Git** (it's already in .gitignore)
2. **Share new Client ID securely:**
   - Slack DM (delete after)
   - Password manager
   - Secure note
3. **Tell them to update their local .env file**

---

## Optional: Additional Security Measures

### 1. Enable Advanced Security Features (Cognito)

```
Cognito → User Pool → Advanced security → Edit

✅ Enable adaptive authentication
✅ Enable compromised credentials check
✅ Set up MFA (optional but recommended)
```

### 2. Set Up CloudWatch Alarms

Monitor for suspicious authentication attempts:
- Failed login attempts > 100/hour
- New user signups > 50/hour
- Token refresh failures

### 3. Review IAM Policies

Ensure your S3 bucket and API Gateway have proper access controls:
- S3 bucket is not public
- API Gateway requires authentication
- Lambda functions have least-privilege IAM roles

---

## Verification Checklist

After rotation, verify:

- [ ] New Cognito Client ID created
- [ ] .env file updated with new Client ID
- [ ] Application tested and working
- [ ] Old Client ID deleted from Cognito
- [ ] Production deployment updated (if applicable)
- [ ] Team members notified (if applicable)
- [ ] No errors in CloudWatch logs
- [ ] Users can login successfully

---

## What About Other Credentials?

### User Pool ID - No Action Needed
- This is public information (in your frontend code)
- Cannot be used maliciously on its own
- No need to rotate

### Identity Pool ID - No Action Needed
- Protected by IAM policies
- Requires authenticated Cognito user
- Low risk

### API Gateway URL - No Action Needed
- Meant to be public
- Protected by Cognito authorizer
- All endpoints require valid JWT token

### S3 Bucket Name - No Action Needed
- Protected by IAM policies
- Not directly accessible
- Requires authenticated access

---

## Timeline

**Immediate (Today):**
- Create new Cognito Client ID
- Update .env file
- Test application

**Within 24 Hours:**
- Delete old Client ID
- Update production deployment

**Within 1 Week:**
- Review security settings
- Set up monitoring

---

## If You Suspect Active Compromise

If you see suspicious activity:

1. **Immediately disable old Client ID** (don't wait for testing)
2. **Check CloudWatch logs** for unusual patterns
3. **Review Cognito user list** for suspicious accounts
4. **Enable MFA** for all users
5. **Contact AWS Support** if needed

---

## Cost Impact

**Creating new App Client:** FREE
**Deleting old App Client:** FREE
**No additional AWS charges**

---

## Questions?

- **Q: Will existing users need to re-login?**
  - A: Yes, once you delete the old Client ID, existing sessions will be invalidated. Users will need to login again.

- **Q: Can I keep both Client IDs active?**
  - A: Yes, temporarily for testing. But delete the old one once confirmed working.

- **Q: What if I forget to update production?**
  - A: Production will break when you delete the old Client ID. Update production first, then delete.

---

**Status:** Ready to execute
**Risk:** Low (if you follow steps)
**Rollback:** Easy (just switch back to old Client ID if needed)
