# Test Service & GCP Setup — Browser & CLI TODOs

## Overview

Deploy the reference FastAPI service (`examples/test-service/`) behind IAP on Cloud Run, then verify tokentoss works end-to-end.

---

## Prerequisites

- [ ] GCP project with billing enabled
- [ ] `gcloud` CLI installed and authenticated (`gcloud auth login`)
- [ ] Set your project ID: `export PROJECT_ID=your-project-id`
- [ ] A domain you control (needed for the SSL certificate and load balancer)

---

## GCP Console Steps (Browser)

### 1. Enable Required APIs

Can be done via CLI or the console **APIs & Services > Enable APIs** page:

```bash
gcloud services enable \
    run.googleapis.com \
    iap.googleapis.com \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID
```

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

### 4. Deploy to Cloud Run

```bash
cd examples/test-service

gcloud run deploy tokentoss-test-service \
    --source=. \
    --region=us-west1 \
    --project=$PROJECT_ID \
    --no-allow-unauthenticated
```

`--no-allow-unauthenticated` is critical — only authenticated requests via IAP or service accounts can reach the service.

Note the service URL from the output (e.g. `https://tokentoss-test-service-xxxxx-uw.a.run.app`). You won't use this URL directly — IAP requires going through the load balancer.

### 5. Set Up Load Balancer

IAP requires an external HTTPS load balancer in front of Cloud Run. Cloud Run's default URL bypasses IAP entirely.

```bash
# Create a serverless network endpoint group (NEG)
gcloud compute network-endpoint-groups create tokentoss-test-neg \
    --region=us-west1 \
    --network-endpoint-type=serverless \
    --cloud-run-service=tokentoss-test-service \
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
    --network-endpoint-group-region=us-west1 \
    --project=$PROJECT_ID

# Create a URL map (routes all traffic to the backend)
gcloud compute url-maps create tokentoss-test-urlmap \
    --default-service=tokentoss-test-backend \
    --project=$PROJECT_ID

# Reserve a static IP address
gcloud compute addresses create tokentoss-test-ip \
    --global \
    --project=$PROJECT_ID

# Get the IP (you need this for DNS)
gcloud compute addresses describe tokentoss-test-ip \
    --global --format='value(address)' \
    --project=$PROJECT_ID
```

### 6. Point DNS at the Load Balancer

1. Go to your **DNS provider** (Cloudflare, Route53, Google Domains, etc.)
2. Create an **A record**:
   - Name: `tokentoss-test` (or whatever subdomain you want)
   - Value: the static IP from step 5
3. Wait for propagation (can be minutes to hours)

### 7. Create SSL Certificate and HTTPS Proxy

```bash
# Create a Google-managed SSL certificate (auto-renewing)
gcloud compute ssl-certificates create tokentoss-test-cert \
    --domains=tokentoss-test.yourdomain.com \
    --project=$PROJECT_ID

# Create the HTTPS proxy
gcloud compute target-https-proxies create tokentoss-test-https-proxy \
    --url-map=tokentoss-test-urlmap \
    --ssl-certificates=tokentoss-test-cert \
    --project=$PROJECT_ID

# Create the forwarding rule (connects the IP to the proxy)
gcloud compute forwarding-rules create tokentoss-test-forwarding \
    --global \
    --target-https-proxy=tokentoss-test-https-proxy \
    --address=tokentoss-test-ip \
    --ports=443 \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID
```

Note: The managed SSL certificate can take 10-60 minutes to provision. It won't work until DNS is propagated and Google can verify domain ownership.

### 8. Enable IAP on the Backend Service

```bash
gcloud iap web enable \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --project=$PROJECT_ID
```

### 9. Add Desktop Client to IAP Programmatic Access

This step is done in the browser:

1. Go to **Security > Identity-Aware Proxy** in GCP Console
2. Find and select the `tokentoss-test-backend` service
3. Open the **Settings** panel (or info panel on the right)
4. Under **Programmatic clients**, add the **Desktop OAuth Client ID** from step 3
5. Save

This tells IAP: "Accept tokens that were issued to the Desktop OAuth client." Without this, tokentoss tokens will be rejected even if the user is authorized.

### 10. Grant User Access to the IAP Resource

```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --member="user:you@gmail.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project=$PROJECT_ID
```

Replace `you@gmail.com` with your actual email. Repeat for each user who needs access.

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

# Use the load balancer URL, NOT the direct Cloud Run URL
client = IAPClient(base_url="https://tokentoss-test.yourdomain.com")

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

Delete all GCP resources when done to avoid charges:

```bash
# Load balancer components
gcloud compute forwarding-rules delete tokentoss-test-forwarding --global -q --project=$PROJECT_ID
gcloud compute target-https-proxies delete tokentoss-test-https-proxy -q --project=$PROJECT_ID
gcloud compute ssl-certificates delete tokentoss-test-cert -q --project=$PROJECT_ID
gcloud compute url-maps delete tokentoss-test-urlmap -q --project=$PROJECT_ID

# Backend and NEG
gcloud compute backend-services delete tokentoss-test-backend --global -q --project=$PROJECT_ID
gcloud compute network-endpoint-groups delete tokentoss-test-neg --region=us-west1 -q --project=$PROJECT_ID

# Static IP
gcloud compute addresses delete tokentoss-test-ip --global -q --project=$PROJECT_ID

# Cloud Run service
gcloud run services delete tokentoss-test-service --region=us-west1 -q --project=$PROJECT_ID
```

Also remove the DNS A record from your DNS provider.

---

## Open Decisions

- **Domain**: Which subdomain will you use for the test service?
- **Region**: `us-west1` is assumed — change if your GCP resources are elsewhere
- **User type**: External (Gmail users) vs Internal (Workspace only)?
- **JWT verification**: The service currently trusts IAP headers without verifying the JWT assertion. Fine for a test service; could add verification later for production use.
