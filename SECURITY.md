# Security Policy

## Reported Security Issues

### ⚠️ CRITICAL: Leaked Firebase API Key (Resolved)

**Issue:** A Firebase API key was previously committed to this repository's source code and remains in the git history.

**Exposed Credential:**
- **API Key:** `AIzaSyCfT3Ln7GM5koSGQKCujtSI7NxfVeOIVbE`
- **Status:** This key has been exposed in git history and should be considered compromised

**Required Action:**
1. **IMMEDIATELY rotate this Firebase API key** in the Firebase Console:
   - Go to [Firebase Console](https://console.firebase.google.com/)
   - Navigate to Project Settings → General
   - Under "Web API Key", click "Reset key" or create a new web app configuration
   - Update your `.env` file with the new key
   - **DO NOT commit the new key to source control**

2. Review Firebase security rules to ensure no unauthorized access occurred while the key was exposed

3. Monitor Firebase usage logs for any suspicious activity during the exposure period

## Security Best Practices

### Credential Management

**DO:**
- ✅ Store all sensitive credentials in `.env` files (these are gitignored)
- ✅ Use environment variables for API keys, database URLs, and secrets
- ✅ Rotate credentials immediately if they are accidentally committed
- ✅ Use `.env.example` files with placeholder values for documentation
- ✅ Review commits before pushing to ensure no secrets are included

**DON'T:**
- ❌ Never commit `.env` files to git
- ❌ Never hardcode API keys, passwords, or tokens in source code
- ❌ Never commit Firebase credentials JSON files
- ❌ Never share credentials in plain text (Slack, email, etc.)

### Firebase Security

This project uses Firebase Authentication. Ensure your Firebase configuration follows these guidelines:

1. **Enable App Check** to prevent unauthorized API usage
2. **Configure Security Rules** for Firestore/Realtime Database (if used)
3. **Set up authorized domains** in Firebase Console under Authentication → Settings
4. **Enable monitoring** to detect unusual authentication patterns
5. **Rotate API keys regularly** as a security best practice

### Required Environment Variables

#### Frontend (`frontend/.env`)
```env
VITE_API_URL=http://localhost:8000
VITE_FIREBASE_API_KEY=your-new-firebase-api-key
VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
VITE_FIREBASE_PROJECT_ID=your-project-id
VITE_FIREBASE_STORAGE_BUCKET=your-project.appspot.com
VITE_FIREBASE_MESSAGING_SENDER_ID=your-sender-id
VITE_FIREBASE_APP_ID=your-app-id
VITE_FIREBASE_MEASUREMENT_ID=your-measurement-id
```

#### Backend (`backend/.env`)
- See `backend/.env.example` for complete list
- Never commit `firebase-credentials.json`

## Reporting Security Vulnerabilities

If you discover a security vulnerability in this project, please report it by:

1. **DO NOT** create a public GitHub issue
2. Email the repository maintainers directly with:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if available)

We will respond to security reports within 48 hours and work to resolve critical issues immediately.

## Security Checklist for Contributors

Before committing code:

- [ ] No API keys or credentials in code
- [ ] No `.env` files committed
- [ ] No Firebase credentials JSON files
- [ ] Environment variables used for all sensitive config
- [ ] `.gitignore` properly excludes sensitive files
- [ ] No hardcoded URLs in production code (use env vars)

## Security Updates

**Last Updated:** 2026-02-07  
**Last Security Audit:** 2026-02-07  
**Known Issues:** Firebase API key exposure (requires rotation)
