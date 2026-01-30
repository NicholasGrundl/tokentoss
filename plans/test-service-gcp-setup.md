# Test Service & GCP Setup — Browser & CLI TODOs

## Overview

Deploy the reference FastAPI service (`examples/test-service/`) behind IAP on Cloud Run using Cloud Run's native IAP integration (no load balancer required), then verify tokentoss works end-to-end.

---

## Prerequisites

- [ ] A domain you own (e.g., `yourllc.com`)
- [ ] Google Cloud Organization set up via Cloud Identity Free (see next section)
- [ ] GCP project with billing enabled, under the Organization
- [ ] `gcloud` CLI installed and authenticated (`gcloud auth login`)
- [ ] Set environment variables:

```bash
export PROJECT_ID=your-project-id
export REGION=us-west1
export SERVICE_NAME=tokentoss-test-service
export PROJECT_NUMBER=$(gcloud projects describe "${PROJECT_ID}" --format="value(projectNumber)")
```

---

## Step 0: Set Up Google Cloud Organization

Cloud Run's native IAP integration requires your GCP project to belong to a Google Cloud Organization. The free way to create one is through **Cloud Identity Free**.

### What Cloud Identity Free gives you

- A Google Cloud **Organization resource** (required for IAP)
- An admin account like `admin@yourllc.com` for managing GCP
- Up to 50 user accounts at no cost (can request more, also free)
- Basic user and group management via Google Admin Console
- SSO and identity management

### What it does NOT include

- **No Gmail** — Cloud Identity Free is identity-only, no email hosting
- No Google Calendar, Drive, Docs, etc. (those are Google Workspace)
- No email inbox at `admin@yourllc.com` unless you set up forwarding separately

### Sign up for Cloud Identity Free

1. Go to the [Cloud Identity Free signup page](https://workspace.google.com/signup/gcpidentity/welcome)
2. Enter your business name (your LLC name)
3. Enter a contact email you already have (e.g., your personal Gmail) — this is for account recovery only
4. Enter your domain (e.g., `yourllc.com`)
5. **Verify domain ownership** — Google will ask you to add a **TXT record** to your domain's DNS:
   - Go to your domain registrar / DNS provider (Cloudflare, Namecheap, Route53, etc.)
   - Add the TXT record Google provides (something like `google-site-verification=xxxx`)
   - Wait for verification (usually minutes, can take up to an hour)
6. Create your first admin account: `admin@yourllc.com` (or whatever you prefer)
   - Set a strong password — this becomes the **super admin** for your Organization
7. Done — you now have a Google Cloud Organization

### Set up email forwarding to your personal email

Since Cloud Identity Free has no Gmail, emails sent to `admin@yourllc.com` will bounce unless you set up forwarding. There are two approaches:

#### Option A: Forward at the DNS / domain level (recommended)

This is the simplest — handle it where your domain is registered, before Google is involved at all.

**If using Cloudflare** (Email Routing):
1. Go to your Cloudflare dashboard > your domain > **Email Routing**
2. Click **Enable Email Routing** if not already enabled
3. Add a route:
   - **Custom address**: `admin@yourllc.com` (or `*` for catch-all)
   - **Destination**: `yourpersonal@gmail.com`
4. Verify your destination email (Cloudflare sends a confirmation link)
5. Cloudflare automatically sets the MX records

**If using Namecheap**:
1. Domain List > Manage > **Email Forwarding** (under "Redirect Email" tab)
2. Add forward: `admin` → `yourpersonal@gmail.com`

**If using another registrar**: Most registrars offer basic email forwarding. Look for "Email Forwarding" or "Email Aliases" in the domain settings.

#### Option B: Forward via Google Admin routing rules

This only works if you also point your domain's MX records to Google (which you wouldn't normally do with Cloud Identity Free since there's no Gmail). Generally **Option A is simpler** unless you have a specific reason to route through Google.

### Move your existing GCP project under the Organization

If you already have a GCP project under your personal Gmail:

1. Go to [Google Cloud Console](https://console.cloud.google.com) > **IAM & Admin > Settings**
2. Click **Migrate** (at the top)
3. Select your new Organization as the destination
4. Confirm

Or via CLI:
```bash
gcloud projects move $PROJECT_ID --organization=ORG_ID
```

To find your Org ID:
```bash
gcloud organizations list
```

### Verify the Organization is set up

```bash
# List your organizations
gcloud organizations list

# Verify your project is under the org
gcloud projects describe $PROJECT_ID --format="value(parent.id)"
```

---

## GCP Console Steps (Browser)

### 1. Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    iap.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID
```

Note: `compute.googleapis.com` is **not** needed — that's only required for the load balancer approach.

### 2. Configure OAuth Consent Screen

This **must** be done in the browser — it's not fully scriptable.

1. Go to **APIs & Services > OAuth consent screen**
2. Choose user type:
   - **External** — for Gmail users (general public, but starts in "testing" mode)
   - **Internal** — for Google Workspace orgs only (all org users allowed automatically)
3. Fill in:
   - **App name**: `tokentoss test`
   - **User support email**: your email
   - **Authorized domains**: your domain (e.g. `yourdomain.com`)
4. Add scopes: `email`, `profile`, `openid`
5. If using **External** in testing mode, add your email under **Test users**
6. Save

### 3. Create Desktop OAuth Client

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Name: `tokentoss-desktop`
5. Click **Create**
6. Note down the **Client ID** and **Client Secret** — you'll need these for tokentoss and for IAP configuration

### 4. Deploy to Cloud Run with IAP Enabled

```bash
cd examples/test-service

gcloud beta run deploy $SERVICE_NAME \
    --source=. \
    --region=$REGION \
    --project=$PROJECT_ID \
    --no-allow-unauthenticated \
    --iap
```

The `--iap` flag enables Cloud Run's native IAP integration directly on the service. No load balancer, no NEG, no SSL certificate, no static IP. IAP is enforced on **all** ingress paths, including the default `*.run.app` URL.

Note the service URL from the output (e.g. `https://tokentoss-test-service-xxxxx-uw.a.run.app`). With native IAP, you use this URL directly.

### 5. Create the IAP Service Agent

The IAP service agent needs permission to invoke your Cloud Run service:

```bash
# Create the IAP service agent (if it doesn't already exist)
gcloud beta services identity create \
    --service=iap.googleapis.com \
    --project=$PROJECT_ID

# Grant the IAP service agent the Cloud Run Invoker role
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com" \
    --role="roles/run.invoker"
```

### 6. Verify IAP is Enabled

```bash
gcloud beta run services describe $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID
```

Look for `Iap Enabled: true` in the output.

### 7. Add Desktop Client to IAP Programmatic Access

This step is done in the browser:

1. Go to **Security > Identity-Aware Proxy** in GCP Console
2. Find and select the `tokentoss-test-service` Cloud Run service
3. Open the **Settings** panel (or info panel on the right)
4. Under **Programmatic clients**, add the **Desktop OAuth Client ID** from step 3
5. Save

This tells IAP: "Accept tokens that were issued to the Desktop OAuth client." Without this, tokentoss tokens will be rejected even if the user is authorized.

### 8. Grant User Access to the IAP Resource

```bash
gcloud beta iap web add-iam-policy-binding \
    --resource-type=cloud-run \
    --service=$SERVICE_NAME \
    --region=$REGION \
    --member="user:you@gmail.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --condition=None \
    --project=$PROJECT_ID
```

Replace `you@gmail.com` with your actual email. Repeat for each user who needs access.

Note: Allow several minutes for IAM policy propagation before testing.

---

## Verify with tokentoss (Jupyter Notebook)

Once all GCP steps are complete:

```python
# 1. Configure tokentoss with your Desktop OAuth credentials (one-time)
from tokentoss import ConfigureWidget
display(ConfigureWidget())
# Enter the Client ID and Client Secret from step 3

# 2. Authenticate — opens a browser window for Google sign-in
from tokentoss import GoogleAuthWidget
widget = GoogleAuthWidget()
display(widget)

# 3. Test the IAP-protected endpoints
from tokentoss import IAPClient

# Use the Cloud Run service URL directly (native IAP — no load balancer URL needed)
client = IAPClient(base_url="https://tokentoss-test-service-xxxxx-uw.a.run.app")

# Verify identity
whoami = client.get_json("/whoami")
print(whoami)
# {'email': 'you@gmail.com', 'user_id': '...', 'iap_jwt_present': True, ...}

# Verify user-specific content
protected = client.get_json("/protected")
print(protected)
# {'email': 'you@gmail.com', 'your_request_count': 1, ...}
```

---

## Local Testing (Without GCP)

For development, run the service locally and simulate IAP headers:

```bash
cd examples/test-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

```bash
# Health check (no auth needed)
curl http://localhost:8080/health

# Simulate IAP headers
curl -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@gmail.com" \
     -H "X-Goog-Authenticated-User-Id: accounts.google.com:12345" \
     http://localhost:8080/whoami
```

---

## Cleanup

```bash
# Delete the Cloud Run service (this also removes the IAP binding)
gcloud run services delete $SERVICE_NAME \
    --region=$REGION \
    --project=$PROJECT_ID \
    -q
```

That's it — no load balancer components, NEGs, static IPs, or SSL certs to tear down.

---

## Open Decisions

- **Region**: `us-west1` is assumed — change if your GCP resources are elsewhere
- **User type**: External (Gmail users) vs Internal (Workspace only)?
- **Organization**: Confirm your GCP project is in a Cloud Organization (required for native Cloud Run IAP)
- **JWT verification**: The service currently trusts IAP headers without verifying the JWT assertion. Fine for a test service; could add verification later for production use.

---

## Appendix: Load Balancer Alternative

The native Cloud Run IAP integration (`--iap` flag) is the recommended approach. However, if you need a load balancer (e.g., your project isn't in a Cloud Organization, or you need custom domain routing, WAF, CDN, or other LB features), here's the full setup.

### Why you might still need a load balancer

- **No Cloud Organization**: Native Cloud Run IAP requires the project to be in a GCP Organization. Personal Gmail-only projects must use the load balancer approach.
- **Custom domain**: If you want a vanity URL like `api.yourdomain.com` instead of the `*.run.app` URL.
- **Cloud Armor / WAF**: Rate limiting, geo-blocking, and DDoS protection require the load balancer.
- **Multi-service routing**: URL-map based routing to multiple backends.

### Why you probably don't

- **Cost**: The load balancer alone costs ~$18/month even with zero traffic. Cloud Run's native IAP adds no cost.
- **Complexity**: The LB approach requires 7+ resources (NEG, backend service, URL map, static IP, SSL cert, HTTPS proxy, forwarding rule). Native IAP is a single `--iap` flag.
- **Maintenance**: More infrastructure to manage, more things that can break, more to clean up.

### Load balancer setup (if needed)

Additional prerequisites:
- [ ] A domain you control (needed for the SSL certificate)
- [ ] Enable Compute API: `gcloud services enable compute.googleapis.com --project=$PROJECT_ID`

Deploy **without** the `--iap` flag:

```bash
gcloud run deploy $SERVICE_NAME \
    --source=. \
    --region=$REGION \
    --project=$PROJECT_ID \
    --no-allow-unauthenticated
```

Then create the load balancer infrastructure:

```bash
# Create a serverless network endpoint group (NEG)
gcloud compute network-endpoint-groups create tokentoss-test-neg \
    --region=$REGION \
    --network-endpoint-type=serverless \
    --cloud-run-service=$SERVICE_NAME \
    --project=$PROJECT_ID

# Create a backend service
gcloud compute backend-services create tokentoss-test-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID

# Attach the NEG to the backend service
gcloud compute backend-services add-backend tokentoss-test-backend \
    --global \
    --network-endpoint-group=tokentoss-test-neg \
    --network-endpoint-group-region=$REGION \
    --project=$PROJECT_ID

# Create a URL map
gcloud compute url-maps create tokentoss-test-urlmap \
    --default-service=tokentoss-test-backend \
    --project=$PROJECT_ID

# Reserve a static IP
gcloud compute addresses create tokentoss-test-ip \
    --global \
    --project=$PROJECT_ID

# Get the IP (needed for DNS — create an A record pointing to this)
gcloud compute addresses describe tokentoss-test-ip \
    --global --format='value(address)' \
    --project=$PROJECT_ID

# Create a Google-managed SSL certificate
gcloud compute ssl-certificates create tokentoss-test-cert \
    --domains=tokentoss-test.yourdomain.com \
    --project=$PROJECT_ID

# Create the HTTPS proxy
gcloud compute target-https-proxies create tokentoss-test-https-proxy \
    --url-map=tokentoss-test-urlmap \
    --ssl-certificates=tokentoss-test-cert \
    --project=$PROJECT_ID

# Create the forwarding rule
gcloud compute forwarding-rules create tokentoss-test-forwarding \
    --global \
    --target-https-proxy=tokentoss-test-https-proxy \
    --address=tokentoss-test-ip \
    --ports=443 \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID
```

Enable IAP on the **backend service** (not on Cloud Run directly):

```bash
gcloud iap web enable \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --project=$PROJECT_ID
```

Grant user access (note: `backend-services` resource type, not `cloud-run`):

```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --member="user:you@gmail.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project=$PROJECT_ID
```

Load balancer cleanup:

```bash
gcloud compute forwarding-rules delete tokentoss-test-forwarding --global -q --project=$PROJECT_ID
gcloud compute target-https-proxies delete tokentoss-test-https-proxy -q --project=$PROJECT_ID
gcloud compute ssl-certificates delete tokentoss-test-cert -q --project=$PROJECT_ID
gcloud compute url-maps delete tokentoss-test-urlmap -q --project=$PROJECT_ID
gcloud compute backend-services delete tokentoss-test-backend --global -q --project=$PROJECT_ID
gcloud compute network-endpoint-groups delete tokentoss-test-neg --region=$REGION -q --project=$PROJECT_ID
gcloud compute addresses delete tokentoss-test-ip --global -q --project=$PROJECT_ID
gcloud run services delete $SERVICE_NAME --region=$REGION -q --project=$PROJECT_ID
```

### References

- [Configure IAP for Cloud Run (official docs)](https://cloud.google.com/run/docs/securing/identity-aware-proxy-cloud-run)
- [Enable IAP for Cloud Run (IAP docs)](https://cloud.google.com/iap/docs/enabling-cloud-run)
- [1-click IAP with Cloud Run (Google Codelab)](https://codelabs.developers.google.com/codelabs/cloud-run/how-to-use-iap-cloud-run)
- [Using IAP with Cloud Run Without a Load Balancer (Medium)](https://medium.com/google-cloud/using-google-identity-aware-proxy-iap-with-cloud-run-without-a-load-balancer-27db89b9ed49)
