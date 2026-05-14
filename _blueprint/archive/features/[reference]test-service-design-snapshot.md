# Test Service: Cloud Run + IAP Verification Microservice

## Purpose

A minimal FastAPI service deployed behind IAP on Cloud Run. Used to:

1. **Verify tokentoss tokens work end-to-end** — confirm that `IAPClient` requests arrive with valid ID tokens
2. **Demonstrate user-specific content** — show how IAP injects the authenticated user's identity into requests
3. **Serve as a living example** for client org admins setting up their own IAP-protected APIs

Lives at `examples/test-service/` in the tokentoss repo. Not published to PyPI (hatchling only packages `src/`).

---

## How IAP Works (Context for Design)

When a request passes through IAP:

1. IAP verifies the ID token in the `Authorization: Bearer <token>` header
2. If valid, IAP **forwards the request** to the backend with additional headers:
   - `X-Goog-Authenticated-User-Email` — e.g. `accounts.google.com:user@gmail.com`
   - `X-Goog-Authenticated-User-Id` — unique user ID
   - `X-Goog-IAP-JWT-Assertion` — a signed JWT that the backend can verify independently
3. If invalid, IAP returns 401/403 before the request reaches the backend

The backend can **trust these headers** because IAP is a network-level gateway — only IAP can set them. For extra security, the backend can also verify the `X-Goog-IAP-JWT-Assertion` JWT directly.

---

## Application Design

### Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `GET` | `/` | Health check / welcome message |
| `GET` | `/whoami` | Returns the authenticated user's identity from IAP headers |
| `GET` | `/protected` | Example protected resource with user-specific content |
| `GET` | `/health` | Simple health check for Cloud Run (no auth needed) |

### `/whoami` Response

```json
{
  "email": "user@gmail.com",
  "user_id": "accounts.google.com:1234567890",
  "iap_jwt_present": true,
  "message": "Hello, user@gmail.com! Your request was authenticated by IAP."
}
```

### `/protected` Response (user-specific content)

```json
{
  "email": "user@gmail.com",
  "greeting": "Welcome back, user@gmail.com!",
  "your_request_count": 1,
  "all_users_seen": ["user@gmail.com", "other@company.com"],
  "note": "Request count is in-memory and resets on deploy."
}
```

Uses a simple in-memory counter per user to demonstrate user-specific state. Not persistent — resets on each deploy, which is fine for a test service.

### `/health` Response

```json
{
  "status": "ok"
}
```

No IAP headers expected. Cloud Run uses this for liveness checks.

---

## File Structure

```
examples/test-service/
    main.py              # FastAPI app (~80 lines)
    Dockerfile           # Container image
    requirements.txt     # Runtime deps (fastapi, uvicorn)
    README.md            # Deploy instructions
```

### `main.py`

```python
from collections import defaultdict

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI(title="tokentoss test service")

# In-memory per-user request counter (resets on deploy)
request_counts: dict[str, int] = defaultdict(int)
users_seen: list[str] = []


def get_iap_user(request: Request) -> dict:
    """Extract IAP user identity from forwarded headers."""
    raw_email = request.headers.get("X-Goog-Authenticated-User-Email", "")
    user_id = request.headers.get("X-Goog-Authenticated-User-Id", "")
    jwt_assertion = request.headers.get("X-Goog-IAP-JWT-Assertion", "")

    # IAP prefixes email with "accounts.google.com:"
    email = raw_email.removeprefix("accounts.google.com:")

    return {
        "email": email,
        "user_id": user_id,
        "iap_jwt_present": bool(jwt_assertion),
    }


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    return {
        "service": "tokentoss-test-service",
        "description": "IAP-protected test API for verifying tokentoss authentication",
        "endpoints": ["/whoami", "/protected", "/health"],
    }


@app.get("/whoami")
def whoami(request: Request):
    user = get_iap_user(request)
    if not user["email"]:
        return JSONResponse(
            status_code=401,
            content={"error": "No IAP user identity found in request headers."},
        )
    return {
        **user,
        "message": f"Hello, {user['email']}! Your request was authenticated by IAP.",
    }


@app.get("/protected")
def protected(request: Request):
    user = get_iap_user(request)
    if not user["email"]:
        return JSONResponse(
            status_code=401,
            content={"error": "No IAP user identity found in request headers."},
        )

    request_counts[user["email"]] += 1
    if user["email"] not in users_seen:
        users_seen.append(user["email"])

    return {
        "email": user["email"],
        "greeting": f"Welcome back, {user['email']}!",
        "your_request_count": request_counts[user["email"]],
        "all_users_seen": users_seen,
        "note": "Request count is in-memory and resets on deploy.",
    }
```

### `Dockerfile`

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### `requirements.txt`

```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
```

---

## GCP Setup: Full End-to-End

### Prerequisites

- A GCP project with billing enabled
- `gcloud` CLI installed and authenticated
- Project ID — referred to as `$PROJECT_ID` below

### Step 1: Enable Required APIs

```bash
gcloud services enable \
    run.googleapis.com \
    iap.googleapis.com \
    compute.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID
```

### Step 2: Build and Deploy to Cloud Run

```bash
cd examples/test-service

# Build and deploy in one step (uses Cloud Build behind the scenes)
gcloud run deploy tokentoss-test-service \
    --source=. \
    --region=us-west1 \
    --project=$PROJECT_ID \
    --no-allow-unauthenticated
```

`--no-allow-unauthenticated` is critical — it means only authenticated requests (via IAP or service accounts) can reach the service.

Note the service URL from the output (e.g. `https://tokentoss-test-service-xxxxx-uw.a.run.app`).

### Step 3: Set Up a Cloud Run Backend Service for IAP

IAP requires a **load balancer** in front of Cloud Run. Cloud Run's default URL bypasses IAP. There are two approaches:

#### Option A: Serverless NEG + External HTTPS Load Balancer (production-grade)

This is the standard approach. It sets up a global HTTPS load balancer with IAP enabled.

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

# Add the NEG to the backend service
gcloud compute backend-services add-backend tokentoss-test-backend \
    --global \
    --network-endpoint-group=tokentoss-test-neg \
    --network-endpoint-group-region=us-west1 \
    --project=$PROJECT_ID

# Create a URL map
gcloud compute url-maps create tokentoss-test-urlmap \
    --default-service=tokentoss-test-backend \
    --project=$PROJECT_ID

# Reserve a static IP
gcloud compute addresses create tokentoss-test-ip \
    --global \
    --project=$PROJECT_ID

# Get the IP address (you'll need this for DNS)
gcloud compute addresses describe tokentoss-test-ip \
    --global --format='value(address)' \
    --project=$PROJECT_ID

# Create a managed SSL certificate (requires a domain pointed at the IP)
# For testing, you can use a self-managed cert or skip HTTPS initially
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

#### Option B: Direct Cloud Run + IAP via ingress settings (simpler, newer)

If your GCP project supports it, Cloud Run now has built-in IAP support without a separate load balancer. Check current docs — this feature has been rolling out.

```bash
# Enable IAP directly on the Cloud Run service (if supported)
gcloud run services update tokentoss-test-service \
    --region=us-west1 \
    --iap \
    --project=$PROJECT_ID
```

**Recommendation:** Start with Option A if you need it working now. Check Option B availability — it significantly reduces infrastructure.

### Step 4: Enable IAP on the Backend Service

```bash
gcloud iap web enable \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --project=$PROJECT_ID
```

### Step 5: Configure OAuth Consent Screen

This must be done in the GCP Console (not easily scriptable):

1. Go to **APIs & Services → OAuth consent screen** in GCP Console
2. Choose **External** user type (for Gmail users) or **Internal** (for Workspace-only)
3. Fill in:
   - App name: `tokentoss test`
   - User support email: your email
   - Authorized domains: your domain
4. Add scopes: `email`, `profile`, `openid`
5. Add test users if using External in testing mode

### Step 6: Create Desktop OAuth Client

In **APIs & Services → Credentials**:

1. Click **Create Credentials → OAuth client ID**
2. Application type: **Desktop app**
3. Name: `tokentoss-desktop`
4. Note the **Client ID** and **Client Secret**

### Step 7: Add Desktop Client to IAP Programmatic Access

In **Security → Identity-Aware Proxy**:

1. Select the backend service
2. Go to **Settings** (or the info panel)
3. Under **Programmatic clients**, add the Desktop OAuth Client ID from Step 6

This tells IAP to accept tokens issued to the Desktop OAuth client, which is what tokentoss uses.

### Step 8: Grant Users Access

```bash
# Grant yourself (or other users) access to the IAP-protected resource
gcloud iap web add-iam-policy-binding \
    --resource-type=backend-services \
    --service=tokentoss-test-backend \
    --member="user:you@gmail.com" \
    --role="roles/iap.httpsResourceAccessor" \
    --project=$PROJECT_ID
```

---

## Verification with tokentoss

Once the service and IAP are set up, verify in Jupyter:

```python
# 1. Configure tokentoss with the Desktop OAuth credentials
from tokentoss import ConfigureWidget
display(ConfigureWidget())
# Enter client_id and client_secret from Step 6

# 2. Authenticate
from tokentoss import GoogleAuthWidget
widget = GoogleAuthWidget()
display(widget)
# Click "Sign in with Google"

# 3. Test the endpoints
from tokentoss import IAPClient

# Use the load balancer URL (not the direct Cloud Run URL)
client = IAPClient(base_url="https://tokentoss-test.yourdomain.com")

# Verify identity
whoami = client.get_json("/whoami")
print(whoami)
# {'email': 'you@gmail.com', 'user_id': '...', 'iap_jwt_present': True, 'message': 'Hello, you@gmail.com!...'}

# Verify user-specific content
protected = client.get_json("/protected")
print(protected)
# {'email': 'you@gmail.com', 'greeting': 'Welcome back!', 'your_request_count': 1, ...}

# Call again to see counter increment
protected2 = client.get_json("/protected")
print(protected2["your_request_count"])  # 2
```

---

## Testing Locally (Without IAP)

For development, run the service locally and simulate IAP headers:

```bash
cd examples/test-service
pip install -r requirements.txt
uvicorn main:app --reload --port 8080
```

```bash
# Simulate IAP headers
curl -H "X-Goog-Authenticated-User-Email: accounts.google.com:test@gmail.com" \
     -H "X-Goog-Authenticated-User-Id: accounts.google.com:12345" \
     http://localhost:8080/whoami

# Health check (no headers needed)
curl http://localhost:8080/health
```

---

## Cleanup

When done testing, tear down the GCP resources to avoid charges:

```bash
# Delete forwarding rule, proxy, cert, URL map
gcloud compute forwarding-rules delete tokentoss-test-forwarding --global -q --project=$PROJECT_ID
gcloud compute target-https-proxies delete tokentoss-test-https-proxy -q --project=$PROJECT_ID
gcloud compute ssl-certificates delete tokentoss-test-cert -q --project=$PROJECT_ID
gcloud compute url-maps delete tokentoss-test-urlmap -q --project=$PROJECT_ID

# Delete backend service and NEG
gcloud compute backend-services delete tokentoss-test-backend --global -q --project=$PROJECT_ID
gcloud compute network-endpoint-groups delete tokentoss-test-neg --region=us-west1 -q --project=$PROJECT_ID

# Delete static IP
gcloud compute addresses delete tokentoss-test-ip --global -q --project=$PROJECT_ID

# Delete Cloud Run service
gcloud run services delete tokentoss-test-service --region=us-west1 -q --project=$PROJECT_ID
```

---

## Files to Create

| File | Purpose |
|------|---------|
| `examples/test-service/main.py` | FastAPI application (~80 lines) |
| `examples/test-service/Dockerfile` | Container image definition |
| `examples/test-service/requirements.txt` | Runtime dependencies |
| `examples/test-service/README.md` | Deploy instructions (condensed version of GCP setup above) |

## Open Questions

- **Domain:** Do you have a domain to point at the load balancer, or should we use the IP directly (requires self-managed cert)?
- **Region:** `us-west1` assumed — change if your other GCP resources are elsewhere
- **JWT verification:** The current design trusts IAP headers. For extra security, the service could verify the `X-Goog-IAP-JWT-Assertion` JWT directly using Google's public keys. Worth adding as a future enhancement, but not needed for a test service.
