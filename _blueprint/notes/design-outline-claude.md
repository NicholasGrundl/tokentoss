# Design Document: Jupyter Notebook OAuth SSO with IAP Access

## 1. Executive Summary

[High-level overview of the project goals, the problem being solved, and the proposed solution. Include the business value and primary stakeholders.]

---

## 2. Goals and Non-Goals

### 2.1 Primary Goals

[Specific, measurable objectives this system must achieve, e.g., "Enable data scientists to authenticate to IAP-protected resources from Jupyter notebooks without manual token management."]

### 2.2 Secondary Goals

[Nice-to-have features that add value but aren't critical for MVP, e.g., "Support for multiple GCP projects" or "Token sharing across notebook sessions."]

### 2.3 Explicit Non-Goals

[What this system will NOT do, to set clear boundaries, e.g., "This system will not support service account impersonation" or "Will not provide audit logging of individual API calls."]

---

## 3. Background and Context

### 3.1 Problem Statement

[Detailed description of the current pain points. Why manual OAuth flows are problematic for notebook users. What workflows are currently broken or inefficient.]

### 3.2 Current State

[Description of existing authentication methods being used, their limitations, and why they don't meet current needs.]

### 3.3 Requirements Analysis

[Functional and non-functional requirements derived from user needs and organizational constraints.]

---

## 4. System Architecture

### 4.1 High-Level Architecture

[Architectural diagram showing: Jupyter Notebook → Custom Library → Google OAuth → IAP-Protected Resource. Include data flow arrows.]

### 4.2 Component Overview

#### 4.2.1 Authentication Module (`auth.py`)

[Description of the OAuth flow implementation, including InstalledAppFlow usage, local server mechanics, and token lifecycle management.]

#### 4.2.2 Configuration Module (`config.py`)

[Implementation of config.py including hardcoded OAuth credentials, scope definitions, and design rationale for embedding secrets in private repository.]

#### 4.2.3 Client Module (`client.py`)

[IAPClient class design, request wrapping logic, and automatic credential management. Include discussion of the corrected IAP authentication method using proper OIDC token fetching instead of service account signing.]

#### 4.2.4 Token Storage

[File system layout for token storage, file permissions (0600), location choice rationale (~/.my_org_iap_token.json), and handling of concurrent access.]

### 4.3 Authentication Flow Diagram

[Sequence diagram showing the complete OAuth flow from notebook execution through browser redirect, token exchange, storage, and subsequent API calls.]

### 4.4 Technology Stack

[List of dependencies: google-auth-oauthlib, google-auth-httplib2, google-auth, requests. Include version constraints and compatibility requirements.]

---

## 5. Security Model

### 5.1 Threat Model

[Analysis of potential security threats including: credential theft, token replay attacks, unauthorized access, quota exhaustion, and internal bad actors.]

### 5.2 Security Controls

#### 5.2.1 OAuth Client Type Selection

[Why Desktop App client type is chosen, how localhost redirect URI provides protection, and limitations of this security boundary.]

#### 5.2.2 IAP/IAM Authorization Layer

[How IAP policies act as the primary security control. Configuration requirements for IAM roles and allowlisting users/groups.]

#### 5.2.3 Token Security

[File permissions, secure storage location, token encryption considerations, and secure deletion on revocation.]

#### 5.2.4 Secret Rotation

[Process for rotating OAuth client secrets, including detection of compromise, emergency rotation procedure, and user impact mitigation.]

### 5.3 Security Residual Risks

[Documentation of accepted risks: hardcoded secrets in private repo, internal lateral movement potential, DoS/quota exhaustion scenarios, and mitigation strategies for each.]

---

## 6. Implementation Plan

### 6.1 Phase 1: GCP Infrastructure Setup

#### 6.1.1 OAuth Client Configuration

[Step-by-step instructions for creating Desktop App OAuth client in GCP Console, configuring consent screen, setting up authorized domains, and extracting credentials.]

#### 6.1.2 IAP-Protected Test Resource

[Instructions for deploying a simple test service (Cloud Run or App Engine) and enabling IAP protection. Include minimal application code requirements.]

#### 6.1.3 IAM Policy Configuration

[How to assign "IAP-secured Web App User" roles to test users, group-based access setup, and verification steps.]

### 6.2 Phase 2: Library Implementation

#### 6.2.1 Project Structure

[Directory layout for the my_org_auth library, packaging setup (setup.py/pyproject.toml), and versioning strategy.]

#### 6.2.2 Config Module Implementation

[Implementation details for config.py, including proper OAuth config structure using "installed" key instead of "web", scope definitions, and configuration validation.]

#### 6.2.3 Auth Module Implementation

[Implementation of login_and_get_credentials() function, error handling for browser failures, token refresh logic, and file I/O operations with proper error handling.]

#### 6.2.4 Client Module Implementation

[IAPClient class implementation with corrected IAP authentication using proper OIDC ID token fetching. Include credential caching strategy and automatic refresh handling.]

### 6.3 Phase 3: Testing and Validation

[Overview of testing phases, test environment requirements, and success criteria for proceeding to production.]

---

## 7. Test Plan

### 7.1 Test Environment Setup

#### 7.1.1 GCP Project Configuration

[Detailed steps for setting up a test GCP project separate from production, including quota settings, billing alerts, and resource cleanup policies.]

#### 7.1.2 Test User Accounts

[Requirements for test accounts: Test User 1 (authorized), Test User 2 (unauthorized), service account for automated testing, and multi-factor authentication setup.]

#### 7.1.3 IAP-Protected Mock Service

[Specification for the mock service: minimal Flask/FastAPI application, health check endpoint, authenticated endpoint returning user info, deployment to Cloud Run with IAP enabled.]

### 7.2 Functional Test Cases

#### 7.2.1 Test Case 1: Initial Authentication Flow

**Objective**: Verify first-time OAuth flow completes successfully.

**Pre-conditions**: [No existing token file, browser available, test user has valid Google account]

**Test Steps**: [Step-by-step instructions for running authentication in Jupyter notebook]

**Expected Results**: [Browser opens and closes, credentials saved to ~/.my_org_iap_token.json with mode 0600, file contains valid refresh token]

**Verification**: [How to verify token file contents, check credential validity, confirm no errors in notebook output]

#### 7.2.2 Test Case 2: Authorized IAP Access

**Objective**: Verify authorized user can access IAP-protected resource.

**Pre-conditions**: [Valid credentials for Test User 1, user has IAP role assigned]

**Test Steps**: [Instantiate IAPClient, make request to IAP-protected endpoint]

**Expected Results**: [HTTP 200 response, response body contains expected user identity information]

**Verification**: [Check HTTP status code, validate response headers include IAP assertions, verify user email in response]

#### 7.2.3 Test Case 3: Unauthorized Access Rejection

**Objective**: Verify unauthorized user is denied IAP access.

**Pre-conditions**: [Valid credentials for Test User 2, user does NOT have IAP role]

**Test Steps**: [Delete existing token file, authenticate as Test User 2, attempt IAP request]

**Expected Results**: [OAuth succeeds (HTTP 200 from Google), IAP request fails with HTTP 403]

**Verification**: [Confirm OAuth flow completed, verify 403 status code from IAP endpoint, check error message indicates authorization failure]

#### 7.2.4 Test Case 4: Token Refresh

**Objective**: Verify expired access tokens are automatically refreshed.

**Pre-conditions**: [Existing token file with valid refresh token]

**Test Steps**: [Manually modify token file to set expires_at to past timestamp, make IAP request without deleting token file]

**Expected Results**: [Request succeeds without browser opening, token file updated with new access token and future expiration]

**Verification**: [No browser interaction occurred, token file timestamps updated, access token value changed, refresh token unchanged]

#### 7.2.5 Test Case 5: Corrupted Token Recovery

**Objective**: Verify system recovers gracefully from corrupted token file.

**Pre-conditions**: [Token file exists but contains invalid JSON or missing required fields]

**Test Steps**: [Corrupt token file, attempt to make IAP request]

**Expected Results**: [System detects corruption, initiates new OAuth flow, overwrites corrupted file with valid credentials]

**Verification**: [Browser opened for re-authentication, new valid token file created, subsequent requests succeed]

#### 7.2.6 Test Case 6: Concurrent Access Handling

**Objective**: Verify multiple notebook kernels can safely access tokens.

**Pre-conditions**: [Valid token file, two Jupyter kernels running simultaneously]

**Test Steps**: [From both kernels, simultaneously trigger requests that require token refresh]

**Expected Results**: [Both requests succeed, no file corruption, at most one re-authentication flow]

**Verification**: [Check both notebook outputs for success, inspect token file for corruption, verify token file modification count]

### 7.3 Security Test Cases

#### 7.3.1 Test Case 7: Token File Permissions

**Objective**: Verify token files are created with secure permissions.

**Pre-conditions**: [No existing token file]

**Test Steps**: [Complete OAuth flow, check file permissions using stat or ls -l]

**Expected Results**: [Token file has permissions 0600 (readable/writable by owner only)]

**Verification**: [Command output shows -rw------- permissions, attempt to read file as different user fails]

#### 7.3.2 Test Case 8: Scope Change Handling

**Objective**: Verify re-authentication when required scopes change.

**Pre-conditions**: [Valid token with initial scopes]

**Test Steps**: [Modify DEFAULT_SCOPES to add new scope, reinstall library, attempt IAP request]

**Expected Results**: [System detects scope mismatch, initiates new OAuth flow with updated scopes, user sees consent screen with new permissions]

**Verification**: [New consent screen displayed, token file contains all new scopes in JSON]

#### 7.3.3 Test Case 9: IAP Client ID Validation

**Objective**: Verify requests fail with incorrect IAP target client ID.

**Pre-conditions**: [Valid user credentials, incorrect IAP target client ID]

**Test Steps**: [Instantiate IAPClient with wrong IAP_TARGET_CLIENT_ID, attempt request]

**Expected Results**: [Request fails with HTTP 401 or 403, error message indicates invalid audience]

**Verification**: [Check response status code, verify error message mentions audience/client ID mismatch]

### 7.4 Error Handling Test Cases

#### 7.4.1 Test Case 10: Network Failure During OAuth

**Objective**: Verify graceful handling of network failures.

**Pre-conditions**: [Simulate network interruption during OAuth flow]

**Test Steps**: [Disconnect network after browser opens but before redirect completes]

**Expected Results**: [Clear error message indicating network failure, no corrupted token file, retry guidance provided]

**Verification**: [Exception message is user-friendly, token file does not exist or is unchanged, notebook remains in working state]

#### 7.4.2 Test Case 11: Headless Environment Detection

**Objective**: Verify system detects inability to open browser.

**Pre-conditions**: [SSH session without DISPLAY variable, no browser available]

**Test Steps**: [Attempt OAuth flow in headless environment]

**Expected Results**: [System detects no browser, provides fallback instructions or CLI-based auth flow, clear error message with manual steps]

**Verification**: [Error message includes manual authentication URL, instructions for copying token, no browser process attempted]

### 7.5 Load and Performance Test Cases

#### 7.5.1 Test Case 12: Rapid Sequential Requests

**Objective**: Verify token caching reduces OAuth overhead.

**Pre-conditions**: [Valid cached credentials]

**Test Steps**: [Make 100 sequential IAP requests in tight loop, measure time per request]

**Expected Results**: [First request may be slower, subsequent requests fast (<100ms), only one token refresh if any]

**Verification**: [Timing logs show improvement after first request, no repeated OAuth flows visible]

#### 7.5.2 Test Case 13: Token Refresh Under Load

**Objective**: Verify token refresh doesn't fail under concurrent load.

**Pre-conditions**: [Expired token, 10 concurrent notebook kernels]

**Test Steps**: [All kernels simultaneously make IAP requests]

**Expected Results**: [All requests eventually succeed, at most one full OAuth re-authentication, no deadlocks or race conditions]

**Verification**: [All notebook outputs show success, token file not corrupted, log analysis shows single refresh operation]

### 7.6 Integration Test Cases

#### 7.6.1 Test Case 14: Full End-to-End Workflow

**Objective**: Verify complete user journey from library installation to data access.

**Pre-conditions**: [Fresh Jupyter environment, no prior authentication]

**Test Steps**: [Install library via pip, import IAPClient, make request to IAP service, process returned data]

**Expected Results**: [Library installs without errors, authentication succeeds on first try, data successfully retrieved and usable]

**Verification**: [All steps complete without manual intervention, notebook successfully processes API response, user experience is smooth]

#### 7.6.2 Test Case 15: Cross-Platform Compatibility

**Objective**: Verify library works on macOS, Linux, and Windows.

**Pre-conditions**: [Test environment for each OS]

**Test Steps**: [Run Test Case 14 on each platform]

**Expected Results**: [All platforms successfully complete authentication and IAP access, token file created in appropriate user directory per OS]

**Verification**: [macOS uses ~/.my_org_iap_token.json, Linux uses ~/.my_org_iap_token.json, Windows uses %USERPROFILE%\.my_org_iap_token.json]

### 7.7 Test Execution Schedule

[Timeline for running test suites: unit tests on every commit, integration tests daily, security tests weekly, full regression before releases]

### 7.8 Success Criteria

[Quantitative thresholds: 100% of critical test cases pass, no security test failures, <5 second authentication time, 99% reliability in token refresh]

### 7.9 Test Reporting

[Format for test results, responsible parties for review, escalation path for test failures, and regression tracking]

---

## 8. Error Handling and Edge Cases

### 8.1 Browser Availability

[Handling for SSH sessions, containerized environments, and headless operation. Fallback mechanisms and clear error messages.]

### 8.2 Token Corruption

[Detection strategies, automatic recovery procedures, and guidance for manual intervention when needed.]

### 8.3 Network Failures

[Retry logic, timeout configuration, offline behavior, and user-facing error messages.]

### 8.4 Scope Changes

[Detection of scope mismatches, forced re-authentication, and backward compatibility considerations.]

### 8.5 Concurrent Access

[File locking mechanisms, race condition prevention, and handling of simultaneous refresh attempts.]

---

## 9. Operational Considerations

### 9.1 Monitoring and Alerting

[Metrics to track: authentication success rate, token refresh failures, IAP access denials, quota usage. Alert thresholds and escalation procedures.]

### 9.2 Logging Strategy

[What to log (authentication events, errors, API calls), what NOT to log (tokens, user PII), log retention policy, and compliance requirements.]

### 9.3 Deployment and Distribution

[How the library will be distributed (private PyPI, Git repository), versioning strategy (semantic versioning), and update notification mechanism.]

### 9.4 Support and Troubleshooting

[Common failure modes and solutions, diagnostic commands for users to run, support escalation path, and known issues documentation.]

### 9.5 Maintenance

[Regular secret rotation schedule, dependency update policy, security patch process, and decommissioning plan.]

---

## 10. Migration and Rollout Plan

### 10.1 Pilot Phase

[Selection criteria for pilot users, limited rollout plan, feedback collection mechanism, and go/no-go decision criteria.]

### 10.2 Gradual Rollout

[Phased approach to broader adoption, rollback plan if issues discovered, communication plan for users, and training materials.]

### 10.3 Migration from Existing Solutions

[If users are currently using other auth methods, provide migration guide, backward compatibility considerations, and timeline for deprecating old methods.]

---

## 11. Documentation

### 11.1 User Documentation

[Quick start guide for data scientists, API reference for IAPClient, troubleshooting guide, and example notebooks demonstrating common use cases.]

### 11.2 Administrator Documentation

[GCP setup guide for platform teams, IAM policy configuration templates, secret rotation procedures, and monitoring setup instructions.]

### 11.3 Developer Documentation

[Architecture decision records (ADRs) explaining key design choices, contribution guidelines for extending the library, and testing guide for contributors.]

---

## 12. Future Enhancements

### 12.1 Potential Improvements

[Features deferred from MVP: service account impersonation support, multi-project credential management, credential sharing across sessions, plugin architecture for custom auth flows]

### 12.2 Research Items

[Areas requiring further investigation: workload identity federation integration, integration with GCP Secret Manager, support for non-Google OAuth providers]

---

## 13. Appendices

### Appendix A: OAuth 2.0 Flow Technical Details

[Deep dive into InstalledAppFlow mechanics, token exchange protocol details, and redirect URI handling]

### Appendix B: IAP Architecture

[How IAP validates tokens, the relationship between OAuth client IDs and IAP client IDs, and IAP header assertion format]

### Appendix C: Security Considerations for Hardcoded Secrets

[Full analysis from red team perspective, threat scenarios, mitigation effectiveness, and decision rationale]

### Appendix D: GCP IAM Role Reference

[Complete list of required IAM roles, minimum permissions needed, and principle of least privilege recommendations]

### Appendix E: Troubleshooting Decision Tree

[Flowchart for diagnosing common authentication failures, step-by-step diagnostic procedures, and resolution paths]

### Appendix F: Code Examples

[Complete working examples of config.py, auth.py, and client.py with extensive inline comments explaining key decisions]

---

## 14. Approval and Sign-off

[Signature blocks for technical lead, security reviewer, platform architect, and product owner with dates]

---

## Document Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | YYYY-MM-DD | [Author] | Initial outline |

---

## References

- [Google OAuth 2.0 Documentation]
- [Identity-Aware Proxy Documentation]
- [google-auth Library Documentation]
- [OAuth 2.0 RFC 6749]
- [OpenID Connect Core Specification]
