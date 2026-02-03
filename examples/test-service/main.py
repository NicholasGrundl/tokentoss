"""tokentoss test service — IAP-protected FastAPI app for end-to-end verification."""

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
