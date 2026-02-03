# tokentoss Test Service

A minimal FastAPI service deployed behind IAP on Cloud Run. Used to verify that tokentoss tokens work end-to-end and demonstrate user-specific content.

## Endpoints

| Method | Path | Auth | Purpose |
|--------|------|------|---------|
| `GET` | `/health` | No | Health check for Cloud Run |
| `GET` | `/` | No | Service info and endpoint list |
| `GET` | `/whoami` | IAP | Returns authenticated user identity |
| `GET` | `/protected` | IAP | User-specific content with request counter |

## Local Testing

Run the service locally and simulate IAP headers:

```bash
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

```bash
# Health check (no auth)
curl http://localhost:8080/health

# Simulate IAP headers
curl -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@gmail.com" \
     -H "X-Goog-Authenticated-User-Id: accounts.google.com:12345" \
     http://localhost:8080/whoami
```

## Deploy to Cloud Run + IAP

### Prerequisites

- GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Set your project: `export PROJECT_ID=your-project-id`

### Step 1: Enable APIs

```bash
gcloud services enable \
    run.googleapis.com \
    iap.googleapis.com \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID
```

### Step 2: Deploy to Cloud Run

```bash
cd examples/test-service

gcloud run deploy tokentoss-test-service \
    --source=. \
    --region=us-west1 \
    --project=$PROJECT_ID \
    --no-allow-unauthenticated
```

Note the service URL from the output.

### Step 3: Set Up Load Balancer with IAP

IAP requires a load balancer in front of Cloud Run (Cloud Run's default URL bypasses IAP).

```bash
# Create serverless NEG
gcloud compute network-endpoint-groups create tokentoss-test-neg \
    --region=us-west1 \
    --network-endpoint-type=serverless \
    --cloud-run-service=tokentoss-test-service \
    --project=$PROJECT_ID

# Create backend service
gcloud compute backend-services create tokentoss-test-backend \
    --global \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID

# Add NEG to backend service
gcloud compute backend-services add-backend tokentoss-test-backend \
    --global \
    --network-endpoint-group=tokentoss-test-neg \
    --network-endpoint-group-region=us-west1 \
    --project=$PROJECT_ID

# Create URL map
gcloud compute url-maps create tokentoss-test-urlmap \
    --default-service=tokentoss-test-backend \
    --project=$PROJECT_ID

# Reserve static IP
gcloud compute addresses create tokentoss-test-ip \
    --global \
    --project=$PROJECT_ID

# Get the IP (needed for DNS)
gcloud compute addresses describe tokentoss-test-ip \
    --global --format='value(address)' \
    --project=$PROJECT_ID

# Create managed SSL certificate (requires a domain pointed at the IP)
gcloud compute ssl-certificates create tokentoss-test-cert \
    --domains=tokentoss-test.yourdomain.com \
    --project=$PROJECT_ID

# Create HTTPS proxy
gcloud compute target-https-proxies create tokentoss-test-https-proxy \
    --url-map=tokentoss-test-urlmap \
    --ssl-certificates=tokentoss-test-cert \
    --project=$PROJECT_ID

# Create forwarding rule
gcloud compute forwarding-rules create tokentoss-test-forwarding \
    --global \
    --target-https-proxy=tokentoss-test-https-proxy \
    --address=tokentoss-test-ip \
    --ports=443 \
    --load-balancing-scheme=EXTERNAL_MANAGED \
    --project=$PROJECT_ID
```

### Step 4: Enable IAP

```bash
gcloud iap web enable \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --project=$PROJECT_ID
```

### Step 5: Configure OAuth

1. Go to **APIs & Services > OAuth consent screen** in GCP Console
2. Choose **External** (for Gmail users) or **Internal** (for Workspace)
3. Fill in app name, support email, authorized domains
4. Add scopes: `email`, `profile`, `openid`

### Step 6: Create Desktop OAuth Client

1. Go to **APIs & Services > Credentials**
2. Click **Create Credentials > OAuth client ID**
3. Application type: **Desktop app**
4. Note the **Client ID** and **Client Secret**

### Step 7: Add Desktop Client to IAP

1. Go to **Security > Identity-Aware Proxy**
2. Select the backend service
3. Under **Programmatic clients**, add the Desktop OAuth Client ID

### Step 8: Grant User Access

```bash
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --member="user:you@gmail.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project=$PROJECT_ID
```

## Verify with tokentoss

```python
from tokentoss import ConfigureWidget, GoogleAuthWidget, IAPClient

# Configure (one-time)
display(ConfigureWidget())

# Authenticate
display(GoogleAuthWidget())

# Test endpoints (use load balancer URL, not direct Cloud Run URL)
client = IAPClient(base_url="https://tokentoss-test.yourdomain.com")
print(client.get_json("/whoami"))
print(client.get_json("/protected"))
```

## Cleanup

Delete all GCP resources to avoid charges:

```bash
gcloud compute forwarding-rules delete tokentoss-test-forwarding --global -q --project=$PROJECT_ID
gcloud compute target-https-proxies delete tokentoss-test-https-proxy -q --project=$PROJECT_ID
gcloud compute ssl-certificates delete tokentoss-test-cert -q --project=$PROJECT_ID
gcloud compute url-maps delete tokentoss-test-urlmap -q --project=$PROJECT_ID
gcloud compute backend-services delete tokentoss-test-backend --global -q --project=$PROJECT_ID
gcloud compute network-endpoint-groups delete tokentoss-test-neg --region=us-west1 -q --project=$PROJECT_ID
gcloud compute addresses delete tokentoss-test-ip --global -q --project=$PROJECT_ID
gcloud run services delete tokentoss-test-service --region=us-west1 -q --project=$PROJECT_ID
```
