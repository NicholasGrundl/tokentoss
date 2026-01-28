# Design & Testing: GCP Project Authentication

*   **Status:** Draft
*   **Author:** Gemini
*   **Stakeholders:** Engineering Team

---

## 1.0 Executive Summary

[A brief, high-level summary of the project. This section will describe the goal of creating a secure, user-friendly Python library for authenticating against Google Cloud IAP-protected resources from a Jupyter environment. It will mention the core technical approach: using a "Desktop app" OAuth 2.0 flow.]

## 2.0 Goals and Objectives

### 2.1 Goals

*   [A list of the high-level goals. For example: "Enable seamless and secure access to IAP-protected services for internal users within a Jupyter notebook environment."]
*   [For example: "Centralize client credential management to simplify the developer experience and improve security posture."]

### 2.2 Non-Goals

*   [A list of what is explicitly out of scope. For example: "This design does not cover service-to-service authentication (Service Accounts)."]
*   [For example: "This library is not intended for use in publicly distributed applications."]

## 3.0 Architecture Overview

[This section will contain a high-level diagram and description of the system components and their interactions. It will illustrate the flow: User -> Jupyter Notebook -> Custom Auth Library -> Google OAuth Service -> IAP-Protected Service.]

### 3.1 Component Diagram

[A placeholder for a Mermaid or ASCII diagram showing the relationship between the user, the client library, Google's authentication services, and the target IAP resource.]

### 3.2 Authentication Flow

[A step-by-step description of the authentication and request process, from the user's initial call to the final, authorized API request. This will be a prose version of the diagram.]

## 4.0 Implementation Details

[This section will contain the canonical, consolidated code and structure for the Python library. It will be the single source of truth, drawing from the research in `plan-v1.md`.]

### 4.1 Library Structure

[A description of the file and module layout, e.g., `my_org_auth/`, `config.py`, `auth.py`, `client.py`.]

### 4.2 `config.py`

[The implementation of `config.py`, including the structure of the `OAUTH_CLIENT_CONFIG` dictionary. This section will explain why the client secrets are embedded in the code for this internal use case.]

### 4.3 `auth.py`

[The implementation of the core authentication logic, including the `login_and_get_credentials` function. It will detail how `InstalledAppFlow.from_client_config` is used and how tokens are stored securely in the user's home directory.]

### 4.4 `client.py`

[The implementation of the user-facing `IAPClient`. This section will explain how it manages credentials, automatically handles token refreshes, and correctly generates the IAP-specific ID token for making authorized requests.]

## 5.0 Security Analysis

[This section will formalize the "Red Team" analysis from the initial plan.]

### 5.1 Threat Model

*   **External Attacker:** [Analysis of the risk of an external attacker obtaining the client secret. Explanation of why the `http://localhost` redirect URI is the primary mitigation.]
*   **Internal User (Bad Actor):** [Analysis of the risk of a legitimate but malicious internal user. Explanation of how IAP/IAM roles are the ultimate gatekeeper for authorization.]
*   **Denial of Service:** [Analysis of the risk of API quota exhaustion and the mitigation strategy (setting GCP quotas and alerts).]

### 5.2 Security Recommendations

[A list of actionable security requirements, such as: "The OAuth Client ID **MUST** be of type 'Desktop app'." and "The IAP-secured resource **MUST** have a restrictive IAM policy."]

## 6.0 Test Plan

[This section will outline the steps to verify the system's correctness and security, based on the test plan in `plan-v1.md`.]

### 6.1 GCP Setup

*   **OAuth Client ID:** [Instructions on creating the 'Desktop app' client.]
*   **Mock IAP Target:** [Instructions on deploying a simple Cloud Run or App Engine service protected by IAP.]
*   **IAM Configuration:** [Instructions on configuring the IAP roles for two test users, one authorized and one unauthorized.]

### 6.2 Test Cases

*   **TC-1: First-Time Authentication (Authorized User):** [Steps to run the flow with an authorized user, expecting success.]
*   **TC-2: IAP Request (Authorized User):** [Steps to make a request to the IAP resource, expecting a 200 OK.]
*   **TC-3: Authentication & IAP Request (Unauthorized User):** [Steps to run the flow with an unauthorized user, expecting the final IAP request to fail with a 403 Forbidden.]
*   **TC-4: Token Refresh:** [Steps to verify that an expired token is automatically refreshed without user interaction.]

## 7.0 Future Considerations

[A section for potential future improvements.]

*   **Secret Management:** [A note on potentially moving to a more advanced secret management solution like GCP Secret Manager if the library's scope expands.]
*   **Cross-Platform Support:** [A note on considerations if this tool were to be used outside of a standard Linux/macOS environment.]
