# Initial Research: Local Auth SSO Flow from jupyter

Dealing with OAuth 2.0 flows, especially the redirection-based **Authorization Code flow**, from a non-web, interactive environment like a Jupyter notebook requires some specific techniques.

Here is the plan for my research:

## 🔨 Tool Code

I will use Google Search to find information on:

1.  How to perform the Google OAuth 2.0 Authorization Code flow without a traditional web server (using a local server or loopback IP).
2.  The best practices for storing Google credentials and refresh tokens within a Python/Jupyter environment.
3.  Details about the `google-auth` Python library's capabilities for local authorization flows (e.g., using a local server or the command line).
4.  How Google IAP authorization integrates with standard Google OAuth flows.
    Hello\! That's a great project. Dealing with browser redirects from an interactive script like a Jupyter notebook is a classic challenge in the OAuth world.

Based on the research, I have a clear and robust technical plan for you that leverages the official **Google Auth Python SDK** and a standard OAuth flow designed for "Installed Applications" (like a desktop app or, in our case, a notebook). This approach handles the local server, browser pop-up, and token exchange automatically.

-----

## 💡 Plan: Jupyter SSO via Localhost Web Server Flow

The best approach is to use the **Local Server Flow** provided by the `google-auth-oauthlib` library. This library is specifically designed to handle the multi-step OAuth dance from a local process by temporarily spinning up a small, local HTTP server.

### Key Components

| Step Goal | Technical Solution | Python Library | Google OAuth Client Type |
| :--- | :--- | :--- | :--- |
| **1. Browser Redirect** | Use the `InstalledAppFlow` to generate the SSO URL and automatically open the user's browser. | `google-auth-oauthlib` | **Desktop app** (Crucial for `http://localhost` redirect URI support) |
| **2. Receive Auth Code** | The `run_local_server()` method starts a temporary HTTP server on a local port (e.g., `http://localhost:8080`) to listen for the redirect. | `google-auth-oauthlib` | `http://localhost:<port>` must be registered as an Authorized Redirect URI. |
| **3. Get/Store Tokens** | The library automatically exchanges the authorization code for the **Access Token** and **Refresh Token** (by including `access_type='offline'` in the flow). The resulting `Credentials` object can be saved. | `google-auth-oauthlib` and `google.oauth2.credentials` | Scopes should include `openid`, `email`, and `profile` (at minimum). |
| **4. Make API Requests** | Use the saved `Credentials` object to wrap a standard `requests` session, ensuring the Access Token is included and automatically refreshed when it expires using the Refresh Token. | `google.auth.transport.requests` | N/A |

-----

## 🗺️ Detailed Step-by-Step Plan

### Phase 1: Google Cloud Setup (Prerequisites)

1.  **Create a Google Cloud Project** (if you don't have one).
2.  **Enable the necessary APIs** (e.g., if you are accessing Google Cloud resources, enable the relevant service APIs).
3.  **Configure the OAuth Consent Screen** and ensure the *User Type* is set appropriately (Internal for Google Workspace users, or Public for wider use).
4.  **Create OAuth 2.0 Client Credentials**:
      * Navigate to **APIs & Services** \> **Credentials**.
      * Click **Create Credentials** \> **OAuth client ID**.
      * For **Application type**, select **Desktop app**. **This is the critical step** that allows using `http://localhost` as the redirect URI.
      * Google will give you a **Client ID** and **Client Secret**. Download the JSON file containing these secrets. Let's call this file `client_secrets.json`.

### Phase 2: Python/Jupyter Implementation

This code would go into a Jupyter notebook cell.

#### Step 1: Install Libraries

```python
!pip install google-auth-oauthlib google-auth-httplib2 google-auth
```

#### Step 2: Run the Local Server Flow

This cell will perform the SSO:

```python
import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests as tr_requests

# --- Configuration ---
# Your downloaded client secrets file
CLIENT_SECRETS_FILE = 'path/to/your/client_secrets.json' 
# Scopes for getting user info and IAP (IAP often just requires openid/email)
# Add other necessary scopes for the APIs you need to call
SCOPES = ['openid', 'email', 'profile', 'https://www.googleapis.com/auth/cloud-platform'] 

# Check if a credentials file exists (for re-use)
# You should choose a secure location. '~/.config/gcloud/jupyter_creds.json' is an option.
TOKEN_FILE = 'jupyter_creds.json'

credentials = None
if os.path.exists(TOKEN_FILE):
    # Load existing credentials, which automatically includes the refresh token
    credentials = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

if not credentials or not credentials.valid:
    if credentials and credentials.expired and credentials.refresh_token:
        # Step 4: Refresh the token automatically if it's expired
        print("Access token expired, refreshing...")
        credentials.refresh(tr_requests.Request())
    else:
        # Step 1 & 2: Initiate the flow and run the local server
        print("Starting new authorization flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, 
            scopes=SCOPES
        )
        
        # This function starts a local web server (http://localhost:port), 
        # opens the browser, and waits for the redirect.
        # access_type='offline' is critical to get a refresh token.
        credentials = flow.run_local_server(
            port=0, # Let the OS pick a free port
            open_browser=True, 
            access_type='offline' 
        )

    # Step 3: Save the new (or refreshed) credentials, including the refresh token
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    print(f"✅ Authorization complete. Credentials saved to {TOKEN_FILE}.")

else:
    print("✅ Existing valid credentials loaded.")

# Store the credentials object for the session
JUPYTER_CREDENTIALS = credentials
print(f"User ID Token: {JUPYTER_CREDENTIALS.id_token}")
```

#### Step 3: Use a Wrapped Requests Function (IAP Access)

For accessing a service secured by **Google IAP**, you need to send a specialized token: a **Signed ID Token** for the *target service's* OAuth Client ID.

Since you are using a user's token (not a service account), the general process is:

1.  Use the `JUPYTER_CREDENTIALS` (which contains an Access Token and Refresh Token) to get a temporary **ID Token** that is specifically signed for the IAP-secured application (the IAP resource's Client ID).
2.  Send this ID Token in the `Authorization: Bearer` header.

<!-- end list -->

```python
# Assuming you have the IAP Client ID for the target service
IAP_CLIENT_ID = 'your-iap-secured-service-client-id.apps.googleusercontent.com' 

def make_iap_request(url, credentials, iap_client_id, **kwargs):
    """
    Makes an authenticated request to an IAP-secured resource.
    
    This function will automatically ensure the Access Token is fresh 
    before attempting to fetch the IAP ID Token.
    """
    
    # Ensure the Access Token is refreshed if needed
    if credentials.expired and credentials.refresh_token:
        credentials.refresh(tr_requests.Request())
        
    # Get the IAP ID Token for the target service's Client ID (audience)
    # The 'google.auth' library handles this step automatically.
    iap_token = google.auth.iam.sign_id_token(
        credentials, 
        iap_client_id, 
        tr_requests.Request()
    )

    # Add the IAP ID Token to the request headers
    headers = {'Authorization': f'Bearer {iap_token}'}
    
    # Use standard requests to make the call
    response = requests.get(url, headers=headers, **kwargs)
    response.raise_for_status() # Raise an exception for bad status codes
    return response

# Example usage in a new cell
import requests
IAP_URL = 'https://your-iap-secured-endpoint.com'

try:
    # Ensure JUPYTER_CREDENTIALS is the Credentials object from Step 2
    response = make_iap_request(IAP_URL, JUPYTER_CREDENTIALS, IAP_CLIENT_ID)
    print(f"IAP Request Success! Status: {response.status_code}")
    # print(response.text)
except Exception as e:
    print(f"IAP Request Failed: {e}")

```

-----

## 🤝 Next Steps

This plan addresses all your requirements:

  * **SSO Link/Pop-up:** Handled by `flow.run_local_server(open_browser=True)`.
  * **Token Callback:** Handled by the local server listening on `http://localhost:port`.
  * **Token Storage:** Handled by saving the `credentials` object to `jupyter_creds.json`, which includes the **Refresh Token**.
  * **Wrapped Requests:** Handled by the `make_iap_request` function, which manages token refreshing and acquiring the IAP-specific ID Token.

# Followup Research: Managing `client_secrets.json`

Our goal is to research how to simplify the user experience and centralize the management of credentials for multiple users within an organization.

We are essentially asking to bake the OAuth **Client ID** and **Client Secret** into our custom library.

Here is the plan for integrating the `client_secrets.json` data into your custom Python library and managing the resulting tokens in a user-friendly, secure manner.

-----

## 🏗️ Phase 1: Client Secrets and Library Structure

### 1\. Hardcoding the Credentials (Safely)

Instead of requiring a file (`client_secrets.json`) that must be manually managed or located by the user, you can embed the credentials directly into a Python module within your custom library.

While it is generally discouraged to hardcode **secrets** in GitHub for public projects, for an **internal organization library** pulled from a private GitHub or artifact repository, this is an acceptable and common practice, as the client ID/secret are designed for user-facing flows (not for server-to-server security).

  * **Structure:** Create a module inside your library, say `my_org_auth/config.py`.

<!-- end list -->

```python
# my_org_auth/config.py

# IMPORTANT: Replace these placeholders with your actual Desktop App Client ID and Secret
OAUTH_CLIENT_CONFIG = {
    "web": {
        "client_id": "YOUR_DESKTOP_APP_CLIENT_ID.apps.googleusercontent.com",
        "project_id": "your-gcp-project-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": "YOUR_DESKTOP_APP_CLIENT_SECRET",
        # The redirect_uris are defined by the library's local server flow (http://localhost)
        "redirect_uris": ["http://localhost"] 
    }
}

# The scopes required for your IAP access and identity retrieval
DEFAULT_SCOPES = [
    'openid', 
    'email', 
    'profile', 
    'https://www.googleapis.com/auth/cloud-platform' # Example scope
]
```

### 2\. Using the In-Memory Configuration

The `google-auth-oauthlib.flow.InstalledAppFlow` function has a factory method that accepts the configuration dictionary directly, avoiding the need for the file path:

  * **Original (File-based):** `flow = InstalledAppFlow.from_client_secrets_file(...)`
  * **New (In-Memory):** `flow = InstalledAppFlow.from_client_config(config.OAUTH_CLIENT_CONFIG, scopes=config.DEFAULT_SCOPES)`

-----

## 🔑 Phase 2: Token Storage and Management (ADC Location)

You requested storing the tokens in the **Application Default Credentials (ADC) location**. While the standard `gcloud auth application-default login` places a user's token file in a specific OS-dependent location (e.g., `~/.config/gcloud/application_default_credentials.json`), we can leverage a similar, consistent approach.

The `google-auth` library ecosystem prefers loading a custom credentials file via an environment variable: `GOOGLE_APPLICATION_CREDENTIALS`.

### 1\. Establishing a Consistent Token Storage Path

We'll define a standard path for the tokens that is relative to the user's home directory (`~`).

```python
# my_org_auth/auth.py

import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
import google.auth.transport.requests as tr_requests
import json

# Import your hardcoded config
from . import config 

# Define the standard token file path for the organization's library
# We'll use a hidden file in the user's home directory for simplicity and consistency.
TOKEN_FILE = os.path.expanduser('~/.my_org_iap_token.json') 

def login_and_get_credentials():
    """
    Performs the full OAuth flow, stores credentials, and returns the object.
    """
    credentials = None
    
    # 1. Try to load existing credentials
    if os.path.exists(TOKEN_FILE):
        try:
            credentials = Credentials.from_authorized_user_file(TOKEN_FILE, config.DEFAULT_SCOPES)
        except Exception:
            # Handle case where file is corrupted or client ID/scopes changed
            credentials = None 
            
    # 2. Check if credentials are still valid (or refresh them)
    if credentials and credentials.expired and credentials.refresh_token:
        print("Access token expired, refreshing automatically...")
        credentials.refresh(tr_requests.Request())
        
    elif not credentials or not credentials.valid:
        # 3. Start a new SSO flow
        print("Starting new Google SSO Authorization flow...")
        flow = InstalledAppFlow.from_client_config(
            config.OAUTH_CLIENT_CONFIG, 
            scopes=config.DEFAULT_SCOPES
        )
        
        # This will open the browser and start the local server
        credentials = flow.run_local_server(port=0, open_browser=True, access_type='offline')

    # 4. Save the new/refreshed credentials to the standard location
    with open(TOKEN_FILE, 'w') as token:
        token.write(credentials.to_json())
    print(f"✅ Authorization complete. Credentials saved to {TOKEN_FILE}")
    
    # Optionally set an environment variable pointing to the file for non-google-auth libraries
    os.environ['MY_ORG_IAP_TOKEN'] = TOKEN_FILE
    
    return credentials
```

-----

## 🧑‍💻 Phase 3: The User-Facing Request Client

The final piece is creating a wrapper class that automatically calls the authentication logic and uses the resulting credentials for IAP requests.

```python
# my_org_auth/client.py

from .auth import login_and_get_credentials, TOKEN_FILE
import requests
import google.auth.iam
import google.auth.transport.requests as tr_requests
from google.oauth2.credentials import Credentials

class IAPClient:
    def __init__(self, iap_client_id: str):
        """
        Initializes the client with the IAP-secured application's Client ID.
        """
        self.iap_client_id = iap_client_id
        self._credentials = None

    def _get_credentials(self) -> Credentials:
        """
        Retrieves credentials, either from the session, the file, or by running SSO.
        """
        if self._credentials and self._credentials.valid:
            return self._credentials
            
        # Try to load from the standard file path first
        if os.path.exists(TOKEN_FILE):
            try:
                # Load from file and check validity/refresh status
                creds = Credentials.from_authorized_user_file(TOKEN_FILE, config.DEFAULT_SCOPES)
                if creds.expired and creds.refresh_token:
                    creds.refresh(tr_requests.Request())
                    # Resave refreshed credentials
                    with open(TOKEN_FILE, 'w') as token:
                        token.write(creds.to_json())
                
                if creds.valid:
                    self._credentials = creds
                    return self._credentials
            except Exception:
                # Fall through to SSO login if load/refresh fails
                pass 
                
        # If loading or refresh fails, run the full interactive login flow
        self._credentials = login_and_get_credentials()
        return self._credentials

    def request(self, url: str, method: str = 'GET', **kwargs):
        """
        Makes an authenticated request to the IAP-secured resource.
        """
        credentials = self._get_credentials()
        
        # Get the IAP ID Token for the target service's Client ID (audience)
        iap_token = google.auth.iam.sign_id_token(
            credentials, 
            self.iap_client_id, 
            tr_requests.Request()
        )

        headers = kwargs.pop('headers', {})
        headers['Authorization'] = f'Bearer {iap_token}'
        
        response = requests.request(method, url, headers=headers, **kwargs)
        response.raise_for_status() 
        return response

```

### User Experience in Jupyter

The final user interaction would be simple:

```python
# Assumes 'my_org_auth' library is installed (pip install git+private_repo)

from my_org_auth.client import IAPClient

# This is the Client ID of the IAP-secured target application/resource
IAP_TARGET_CLIENT_ID = '123456789-abcdefghijklm.apps.googleusercontent.com' 
TARGET_URL = 'https://my-iap-secured-app.org'

# 1. Instantiate the client. This internally checks for tokens.
client = IAPClient(IAP_TARGET_CLIENT_ID)

# 2. The first time this is run, it will trigger the browser SSO and save the token.
# Subsequent runs will load the saved token and refresh it automatically.
response = client.request(TARGET_URL + '/api/data') 

print(response.json())
```

-----

## 🚀 Plan Summary

1.  **Google Cloud Console:** Create an **OAuth Client ID** of type **Desktop app**.
2.  **Library Code:** Embed the Client ID and Secret directly into a configuration module (`config.py`).
3.  **Authentication Logic (`auth.py`):** Use `InstalledAppFlow.from_client_config()` to avoid the secrets file. The `login_and_get_credentials` function handles the browser pop-up, local server, and saves the final `Credentials` object (including the Refresh Token) to a standard, hidden file location (`~/.my_org_iap_token.json`).
4.  **Wrapper Client (`client.py`):** The `IAPClient` automatically loads the stored credentials, refreshes them when necessary, and uses the IAP-specific token exchange (`google.auth.iam.sign_id_token`) before making the final request.

This approach achieves your goal of a smooth, file-less SSO experience for the end-user while centralizing credential management within your organization's custom library.

# Red team perspective: Security implications of hard coded `client_secrets.json`

Our red team approach reveals that while hardcoding the secrets in a **private repository** carries residual risk, the architectural constraints of the chosen **"Desktop app" OAuth flow** provide significant protection against external attackers.

Here is the security analysis of the scenario.

---

## 🛡️ Security Analysis of Hardcoded Desktop App Secrets

### 1. The Core Protection: The Redirect URI

The most critical factor mitigating risk is the **Desktop App** client type and its associated, fixed redirect URI: `http://localhost:<port>`.

| Scenario | Risk Assessment | Mitigating Factor (Desktop Flow) |
| :--- | :--- | :--- |
| **External Attacker Obtains Secret** | **Low Risk.** An attacker needs to initiate the flow, but they cannot complete it remotely. | Google's OAuth server **only redirects the Authorization Code** to a `localhost` address (or a few other fixed non-public URIs). The attacker would need to be running a local web server **on the victim's machine** to capture the code. |
| **External Attacker Tries Impersonation** | **Blocked.** Impersonating a client requires the attacker to set a redirect URI they control. | The attacker *cannot* change the registered redirect URI for the **Desktop app** client type to their own public server (e.g., `https://evil.com`). The Google server will refuse to redirect the user to a non-local address. |
| **User (Internal Bad Actor) Obtains Secret** | **Elevated Risk.** An internal user can use the secret to run the flow on their own machine. | The flow still requires the user to **successfully authenticate and grant consent** with their Google account. If the bad actor is not an authorized member of the Google Workspace or the IAP group, the process is stopped by the **Authorization Layer** (IAP or the Google consent screen). |

---

### 2. Scenario Red Team Research

#### 1. What if a bad actor gets access to the source code with the client secrets? Can they still log in?

**Answer: Yes, but only for users they control, and crucially, they cannot get tokens for unauthorized users.**

* **The Attack:** A bad actor (e.g., a contractor whose account was compromised, or an external hacker) obtains the Client ID and Client Secret from your private GitHub repo.
* **The Attempt:** The attacker copies your authentication logic and runs it on their own machine.
    * They are redirected to the Google login page.
    * They log in using **their own Google account**.
    * Google redirects the authorization code back to `http://localhost:<port>` on the attacker's machine.
* **The Result (Authorization Failure):**
    * If the attacker's Google account **is not** one of the accounts whitelisted in the Google Cloud Console (via IAM/IAP permissions or the OAuth Consent Screen's user type restriction), the user consent screen or the final IAP request will fail.
    * They cannot use the Client Secret to impersonate someone else or bypass the browser flow; they still need a valid Google user to successfully complete the SSO and authorization steps.
* **Conclusion:** The **authorization layer (IAP/IAM)**, which checks the user's email domain or group membership, is the **primary security control**, not the secrecy of the Client Secret.

---

#### 2. Other Scenarios That Might Happen

| Scenario | Implication & Mitigation |
| :--- | :--- |
| **Denial of Service (DoS) / Quota Exhaustion** | **High Risk.** An attacker can repeatedly call the Google Token Exchange endpoint (`https://oauth2.googleapis.com/token`) using the stolen Client Secret and *fake* authorization codes, potentially spiking your Google API usage quota, incurring cost, or triggering rate limits/suspensions on the OAuth Client. | **Mitigation:** Set strong **API Quota limits** on your GCP project. Set up **alerts** for OAuth token exchange spikes. |
| **Phishing/Social Engineering** | **Moderate Risk.** While the redirect is protected, a skilled attacker could leverage the known, legitimate Client ID to create a highly convincing phishing page. | **Mitigation:** The best defense is user education and reliance on **MFA/2FA** on user accounts. |
| **Internal Lateral Movement** | **Highest Risk.** If the bad actor is an **authorized employee** who has the secret, they can use it to create unauthorized scripts and tools, bypassing standard logging or approval processes that might be built around official tools. | **Mitigation:** Implement strong **source code scanning** for secrets even in private repos and have a process for **rapid secret rotation** if a developer's machine/account is compromised. The *least privilege* principle on the final IAP-secured resource is also key. |

---

## ✅ Recommendation and Path Forward

Based on this analysis, the plan to hardcode the Desktop App Client ID and Secret in a private repository is a **secure and pragmatic choice** for an internal organizational tool, provided the following are strictly maintained:

1.  **Client Type is "Desktop app":** This is essential to enforce the `http://localhost` redirect URI.
2.  **IAP/IAM Whitelisting:** The IAP-secured resource must have an **IAM policy** that only grants the "IAP-secured Web App User" role to authorized users/groups in your organization. This is the **ultimate gatekeeper**.
3.  **Client Secret Rotation:** Have an established, tested process for **revoking and replacing** the Client Secret quickly if the repository (or a developer's access to it) is ever compromised.


# Test Plan: Verify on personal GCP

Verifying the end-to-end flow with explicit authorization checks is the best way to validate the security model before moving to a fully shared system.

We will focus on creating a mock IAP-secured target and testing the authentication flow using two distinct Google accounts to confirm your authorization logic works.

-----

## 🔬 Test Plan Overview: Jupyter SSO Verification

The test plan involves three main phases: **GCP Setup**, **Test Harness Creation** (your custom library functions), and **Execution/Verification**.

### Phase 1: Google Cloud Setup & Mock Target (The Gate)

The goal is to create a secure endpoint that only specific, authenticated users can reach.

| Step | Action | Purpose |
| :--- | :--- | :--- |
| **1. OAuth Client ID** | In GCP Console \> Credentials: Create a new **OAuth Client ID** of type **Desktop App**. Download the JSON, but only extract the **Client ID** and **Client Secret** for hardcoding. | Validates the core Desktop Flow setup. |
| **2. Target Service (Mock IAP)** | Deploy a simple, publicly accessible web service (e.g., on Cloud Run, App Engine, or a VM behind a Load Balancer) that is protected by **Identity-Aware Proxy (IAP)**. | Provides a live endpoint to test the final authentication token against. |
| **3. IAM/IAP Roles (The Authorization Check)** | Go to the IAP settings for the deployed service. Assign the **"IAP-secured Web App User"** role to: | Verifies authorization control. |
| | a) **Test User 1** (Your personal Gmail address). | **Expected Result:** SUCCESS |
| | b) **Test User 2** (Your second, external email address). | **Expected Result:** FAILURE (if not in the allowlist) or SUCCESS (if added) |

### Phase 2: Python/Jupyter Test Harness (The Client)

We will use the module structure we designed to create the authentication function and the requests wrapper.

| Module | Function | Action |
| :--- | :--- | :--- |
| `config.py` | `OAUTH_CLIENT_CONFIG`, `DEFAULT_SCOPES` | Hardcode the **Client ID** and **Client Secret** from Step 1. Define scopes (`openid`, `email`, etc.). |
| `auth.py` | `login_and_get_credentials()` | Implement the full `InstalledAppFlow.from_client_config` logic. This will launch the browser and save tokens to `~/.my_org_iap_token.json`. |
| `client.py` | `IAPClient.request()` | Implement the requests wrapper. This function must handle: **1. Refreshing the Access Token** using the Refresh Token. **2. Acquiring the IAP-specific ID Token** (`google.auth.iam.sign_id_token`) using the IAP target's Client ID as the audience. |

### Phase 3: Execution and Verification (The Test)

This phase runs entirely within the Jupyter notebook.

| Step | User Account | Action in Jupyter Cell | Expected Verification |
| :--- | :--- | :--- | :--- |
| **A. Initial Flow** | **Test User 1** (Personal Gmail) | Run `creds_user1 = auth.login_and_get_credentials()` and complete the browser SSO using **User 1**. | ✅ Browser opens, closes. `credentials` object is returned and saved to `~/.my_org_iap_token.json`. |
| **B. IAP Success** | **Test User 1** | Run `client.request(IAP_URL)`. | ✅ Request succeeds (e.g., returns status code 200). This verifies token refreshing and IAP ID token generation. |
| **C. User Change/Failure** | **Test User 2** (External Email) | **CRITICAL:** Delete `~/.my_org_iap_token.json` first. Run `creds_user2 = auth.login_and_get_credentials()` and complete the SSO using **User 2**. | ✅ SSO succeeds (User 2 logs into Google). The token is saved. |
| **D. Authorization Check** | **Test User 2** | Run `client.request(IAP_URL)`. **If User 2 is NOT in the IAP allowlist...** | 🛑 Request **FAILS** (e.g., returns status code 403 or 401). This confirms IAP is correctly enforcing the IAM policy, validating our security model. |
| **E. Token Refresh Verification** | **Test User 1** | **Wait 1 hour** (or manually edit the `expires_at` in the token file to a past time). Rerun `client.request(IAP_URL)` with User 1's credentials. | ✅ Request succeeds **without opening the browser**. This confirms the **Refresh Token** logic is automatic and working. |

-----

## 🛠️ Placeholder Code Outline

We'll use three small placeholder modules for this test harness:

### 1\. `my_org_auth/config.py` (Placeholders)

```python
# Replace these with your actual Desktop App Client ID and Secret
OAUTH_CLIENT_CONFIG = {
    "web": {
        "client_id": "YOUR_DESKTOP_APP_CLIENT_ID.apps.googleusercontent.com",
        "client_secret": "YOUR_DESKTOP_APP_CLIENT_SECRET",
        "redirect_uris": ["http://localhost"] # Required for from_client_config
    }
}

# The IAP target client ID (Audience) for the secure resource
IAP_TARGET_CLIENT_ID = 'YOUR_IAP_SECURED_SERVICE_CLIENT_ID.apps.googleusercontent.com'

DEFAULT_SCOPES = [
    'openid', 
    'email', 
    'profile', 
    'https://www.googleapis.com/auth/cloud-platform'
]

TOKEN_FILE = os.path.expanduser('~/.my_org_iap_token.json')
```

### 2\. `my_org_auth/auth.py` (SSO Logic)

This will contain the logic from the previous step, using `InstalledAppFlow.from_client_config`.

### 3\. `my_org_auth/client.py` (IAP Request Wrapper)

This will contain the `IAPClient` class and its `request` method, using the `google.auth.iam.sign_id_token` function, which is the key to programmatic IAP access.
