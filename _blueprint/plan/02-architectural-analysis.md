# Project Architectural Analysis

This document outlines architectural observations and potential areas for improvement within the `tokentoss` codebase, focused on enhancing robustness and scalability beyond the initial Jupyter-centric implementation.

## 1. Architectural Limitation: "Detached" Token Refresh

### Current State
In `IAPClient._try_storage`, the client loads token data directly from disk. If the stored ID token is expired, the method returns `None`, leading to a `NoCredentialsError`. 

### The Issue
The `IAPClient` currently lacks the capability to refresh tokens when operating in "detached" mode (e.g., in a standalone CLI script after a prior login session). Even if a valid `refresh_token` exists in the storage file, `IAPClient` does not have access to the `ClientConfig` (client_id/client_secret) required to perform the refresh exchange.

### Impact
Users must re-authenticate (triggering the widget/browser flow) every time their ID token expires (typically 1 hour) if they are not using an active `AuthManager` instance within the same process.

### Recommendation
*   **Optional Config for Client:** Allow `IAPClient` to accept an optional `client_secrets_path` or `ClientConfig`.
*   **Lazy AuthManager:** If config is provided and storage is used, `IAPClient` should be able to instantiate a "headless" `AuthManager` internally to perform background refreshes using the stored refresh token.

## 2. Global State Management (`tokentoss.CREDENTIALS`)

### Current State
The library uses a module-level global `tokentoss.CREDENTIALS` as a fallback in the discovery chain. This is likely set by the `AuthManager` during the widget authentication flow.

### The Issue
While highly convenient for "zero-config" Jupyter Notebook usage, reliance on global state introduces hidden coupling:
*   **Race Conditions:** Multiple widget instances in a single kernel could overwrite each other's credentials.
*   **Session Isolation:** Users attempting to manage connections to multiple different IAP-protected services (with different client IDs) may face configuration collisions.

### Recommendation
*   **Explicit over Implicit:** Encourage the pattern of passing `AuthManager` directly to `IAPClient` in documentation for non-trivial use cases.
*   **Context Management:** Consider a context manager or a "session registry" if multiple credentials need to be managed simultaneously without polluting the global namespace.

## 3. Storage Security & Scalability

### Current State
`FileStorage` correctly enforces `0600` permissions on Unix-like systems, which is excellent for security.

### Observations
*   **Platform Specifics:** Ensure the permission logic handles Windows ACLs if cross-platform parity is a goal (currently focused on `os.chmod` which has limited effect on Windows).
*   **Concurrency:** If multiple processes attempt to write to the same token file simultaneously (e.g., two scripts refreshing at once), there is no file locking mechanism. For high-concurrency environments, a simple file lock (like `fcntl`) would prevent token corruption.
