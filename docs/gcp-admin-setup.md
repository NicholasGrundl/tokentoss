# GCP Admin Setup Guide

How to configure GCP so your users can authenticate with tokentoss.

This guide is for **GCP project administrators**. End users should see the [Quick Start](quickstart.md).

## Overview

tokentoss uses a Desktop OAuth client to authenticate users via Google's Authorization Code flow with PKCE. The flow is:

```
User (Jupyter) → tokentoss → Google OAuth → ID token → IAP → Your Service
```

You need to:
1. Configure an OAuth consent screen
2. Create a Desktop OAuth client
3. Register the client with IAP
4. Grant users access
5. Share credentials with your users

## Step 1: Configure OAuth Consent Screen

Navigate to **GCP Console > APIs & Services > OAuth consent screen**.

**User type:**
- **Internal** — For Google Workspace organizations. Only users in your org can authenticate. No app verification needed. Choose this if all your users have `@yourcompany.com` accounts.
- **External** — For users with personal Gmail accounts or mixed organizations. Requires app verification for production use (you can add test users during development).

**Required fields:**
- App name (e.g., "Data Access" or your service name)
- User support email
- Authorized domains (your organization's domain)

**Scopes — add these three:**
- `openid`
- `email`
- `profile`

If using External type in testing mode, add the email addresses of your test users.

## Step 2: Create Desktop OAuth Client

Navigate to **GCP Console > APIs & Services > Credentials**.

1. Click **Create Credentials > OAuth client ID**
2. Application type: **Desktop app** (not "Web application")
3. Name: `tokentoss-desktop` (or your convention)

Copy the **Client ID** and **Client Secret**. You'll share these with your users.

> **Note:** Desktop OAuth credentials are "public" client secrets per the OAuth 2.0 spec — they identify the application but cannot be used to generate tokens without user consent. tokentoss adds PKCE for additional security.

## Step 3: Add Desktop Client to IAP Programmatic Access

Navigate to **GCP Console > Security > Identity-Aware Proxy**.

1. Find your IAP-protected resource (backend service or App Engine app)
2. Click the resource, then open the info panel or Settings tab
3. Under **Programmatic clients**, add the Desktop OAuth Client ID from Step 2

This tells IAP to accept ID tokens issued to your Desktop OAuth client. Without this step, tokentoss requests will be rejected even with valid tokens.

## Step 4: Grant Users IAP Access

Users need the `roles/iap.httpsResourceAccessor` role.

**Via gcloud (individual users):**

```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=YOUR_BACKEND_SERVICE \
    --member="user:employee@yourcompany.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project=$PROJECT_ID
```

**Via GCP Console (groups):**

1. Navigate to **Security > Identity-Aware Proxy**
2. Select the resource
3. Click **Add Principal**
4. Enter an email address or Google Group
5. Assign role: **IAP-secured Web App User**

Using Google Groups is recommended for managing access at scale.

## Step 5: Distribute Credentials to Users

Provide each user with:

1. **Client ID** (from Step 2)
2. **Client Secret** (from Step 2)
3. **Service base URL** (e.g., `https://your-service.run.app`)
4. Link to the [tokentoss Quick Start](quickstart.md)

**Distribution methods:**
- Internal wiki or shared document (not public)
- Direct message (Slack, email) to authorized users
- Include alongside your service's own onboarding docs

## Security Notes

- Desktop OAuth credentials identify the app but can't impersonate users — user consent is always required
- tokentoss uses PKCE to protect against authorization code interception
- Tokens are stored locally with restrictive file permissions (`0600` on Unix)
- Review IAP access periodically and remove users who no longer need it
- Refresh tokens can be revoked per-user in GCP Console > Security > IAP

## Multiple Environments

If you have separate dev/staging/prod environments:

- **Option A (simpler):** One OAuth client for all environments. Users configure once.
- **Option B (stricter):** Separate OAuth clients per environment. Better audit trail, but users must configure each environment separately.

Both options work with tokentoss. Option A is recommended for most teams.

## Troubleshooting

**Users getting "Permission denied"** — Verify the user has the `roles/iap.httpsResourceAccessor` role on the correct resource.

**Users getting "Invalid OAuth client"** — Confirm the Desktop client ID is added to IAP's programmatic access allowlist (Step 3).

**OAuth consent screen errors** — Ensure all required fields are filled and your domain is verified in GCP.

**"Access blocked: app not verified"** — If using External type, either add the user as a test user or submit the app for verification.
