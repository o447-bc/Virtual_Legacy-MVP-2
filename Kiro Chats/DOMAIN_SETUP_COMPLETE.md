# Domain Setup Complete - SoulReel.net

**Date:** February 14, 2026  
**Status:** ✓ LIVE AND OPERATIONAL

---

## Domain Information

**Domain:** soulreel.net  
**Registrar:** AWS Route 53  
**Cost:** $12/year  
**Auto-Renew:** Enabled  
**Expiry:** February 14, 2027  

---

## Live URLs

### Primary Domain
**https://soulreel.net** ✓ LIVE  
**https://www.soulreel.net** ✓ LIVE

### Backup URL (Amplify)
**https://main.d33jt7rnrasyvj.amplifyapp.com** ✓ ACTIVE

---

## SSL/TLS Certificate

**Provider:** AWS Certificate Manager (ACM)  
**Type:** Amplify Managed  
**Status:** AVAILABLE ✓  
**Auto-Renewal:** Yes  
**HTTPS:** Enforced (automatic redirect from HTTP)

---

## DNS Configuration

**Hosted Zone ID:** Z0788634X75IWFG4NCBY  
**Name Servers:** Managed by Route 53

**DNS Records:**
- `soulreel.net` → A (ALIAS) → CloudFront Distribution
- `www.soulreel.net` → CNAME → CloudFront Distribution
- SSL Validation → CNAME → ACM Validation

---

## Backend Configuration

**CORS Updated:** ✓  
**Allowed Origin:** https://soulreel.net  
**API Gateway:** https://qu5zn6mns1.execute-api.us-east-1.amazonaws.com/Prod  
**WebSocket:** wss://tfdjq4d1r6.execute-api.us-east-1.amazonaws.com/prod

---

## Deployment Summary

### What Was Completed:

1. ✓ Registered soulreel.net domain via Route 53
2. ✓ Created Amplify domain association
3. ✓ Configured automatic SSL certificate
4. ✓ Set up DNS records (A and CNAME)
5. ✓ Updated backend CORS configuration
6. ✓ Deployed backend with new CORS settings
7. ✓ Verified domain is AVAILABLE and live

### Timeline:
- Domain Registration: 2:19 PM CST
- DNS Configuration: 2:44 PM CST
- CORS Update: 2:45 PM CST
- Status: AVAILABLE: 2:47 PM CST

**Total Setup Time:** ~30 minutes

---

## Security Features

✓ **HTTPS Only** - Automatic HTTP → HTTPS redirect  
✓ **SSL/TLS Certificate** - Free, auto-renewing  
✓ **WHOIS Privacy** - Personal information protected  
✓ **CloudFront CDN** - DDoS protection, global distribution  
✓ **CORS** - Restricted to soulreel.net only

---

## Future Enhancements (Optional)

### Recommended:
- Add security headers (HSTS, X-Frame-Options, etc.)
- Set up AWS WAF for advanced protection
- Configure CloudWatch alarms for monitoring
- Add staging subdomain (staging.soulreel.net)

### Custom Subdomains:
- `api.soulreel.net` - Direct API access
- `staging.soulreel.net` - Staging environment
- `dev.soulreel.net` - Development environment

---

## Maintenance

### Annual Tasks:
- Domain auto-renews on February 14, 2027
- SSL certificate auto-renews (no action needed)
- Monitor costs in AWS Billing Dashboard

### Monthly Costs:
- Domain: $1/month ($12/year)
- Amplify Hosting: $0 (free tier)
- CloudFront: ~$0-2/month (low traffic)
- **Total: ~$1-3/month**

---

## Testing Checklist

Test your new domain:

- [ ] Visit https://soulreel.net
- [ ] Visit https://www.soulreel.net
- [ ] Verify HTTPS (lock icon in browser)
- [ ] Test signup/login functionality
- [ ] Check browser console for CORS errors (should be none)
- [ ] Test on mobile device
- [ ] Test video recording (if applicable)

---

## Quick Commands

### Check Domain Status
```bash
aws route53domains list-domains --region us-east-1
```

### Check Amplify Domain Status
```bash
aws amplify get-domain-association \
  --app-id d33jt7rnrasyvj \
  --domain-name soulreel.net \
  --region us-east-1
```

### View DNS Records
```bash
aws route53 list-resource-record-sets \
  --hosted-zone-id Z0788634X75IWFG4NCBY
```

### Update CORS (if needed)
```bash
# Edit SamLambda/template.yml
# Change AllowOrigin value
# Then:
cd SamLambda
sam build && sam deploy --no-confirm-changeset
```

---

## Support Resources

- **Route 53 Console:** https://console.aws.amazon.com/route53/
- **Amplify Console:** https://console.aws.amazon.com/amplify/
- **Certificate Manager:** https://console.aws.amazon.com/acm/
- **Billing Dashboard:** https://console.aws.amazon.com/billing/

---

## Congratulations! 🎉

Your app is now live at **https://soulreel.net** with:
- Professional custom domain
- Automatic HTTPS encryption
- Global CDN distribution
- Secure backend integration

**Share your app with the world!**
