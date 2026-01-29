# Widget Testing Feedback

Collected during manual testing walkthrough. Items here are candidates for the widgets subpackage refactor (blueprint `03-widgets-subpackage.md`).

---

## ConfigureWidget

### 1. Add optional "Advanced" section with project_id field
- `configure_from_credentials()` already accepts `project_id` but it's not exposed in the widget UI
- Project ID isn't required for the OAuth flow — it's just metadata carried in `client_secrets.json`
- **Proposal:** Add a collapsible/accordion "Advanced" section below the main fields with an optional `Project ID` text input
- **Priority:** Low — nice-to-have for v0.2.0, bundle with widgets refactor

---

## GoogleAuthWidget

*(to be filled as testing continues)*

---

## IAPClient

*(to be filled as testing continues)*
