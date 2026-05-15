# Resource Links

Documentation: https://docs.gspread.org/en/v6.1.4/
Github: https://github.com/burnash/gspread


# General Ecosystem Guidance

## 1. Core Library: `gspread`

* **Role**: The primary high-level Pythonic client for Google Sheets API v4.
* **Philosophy**: Abstracts low-level JSON payloads into intuitive Python objects (`Spreadsheet`, `Worksheet`, `Cell`).
* **Key Operations**:
* `open_by_key()`, `open_by_url()`
* `append_row()`, `update()`, `get_all_records()`
* `batch_update()` (Critical for minimizing API calls).



## 2. Extension Libraries

Use these when `gspread` (which focuses on data) is insufficient for "presentation" or "data structures."

| Library | When to Use | Why? |
| --- | --- | --- |
| **`gspread-formatting`** | UI/UX design in Sheets | `gspread` lacks native methods for cell colors, borders, fonts, and conditional formatting. |
| **`gspread-pandas`** | Data Analysis / Data Science | Direct integration with DataFrames. Handles headers and indexing automatically. |
| **`gspread-dataframe`** | Bulk Data Transfer | Faster and more lightweight than `gspread-pandas` if you only need to push/pull DataFrames without complex sync logic. |

## 3. Quota Limits & Resilience

As of 2026, Google Sheets API enforces strict rate limits.

* **Default Limits**: Generally **300 requests per 60 seconds** per project (60 per user per 60s).
* **The Error**: `APIError 429: RESOURCE_EXHAUSTED`.
* **Resilience Pattern**:
* **Exponential Backoff**: Do not simply sleep for 1 second. Implement a backoff (1s, 2s, 4s, 8s...).
* **Batching**: Use `worksheet.update('A1', [[...]])` for 2D arrays instead of looping through `update_cell()`. One batch call = 1 request; 100 individual cell calls = 100 requests.



## 4. Authentication: Service Accounts vs. Access Tokens

| Method | Type | Best For... | Commentary |
| --- | --- | --- | --- |
| **Service Account** | Server-to-Server | Automated scripts, CRON jobs, Backend APIs. | **Standard.** Uses a `.json` key file. The "Bot" must be shared on the Sheet via its email address. No user interaction required. |
| **OAuth (Access Tokens)** | User-to-Server | Apps where users access *their own* private sheets. | Requires a browser login (consent screen). Generates short-lived tokens and long-lived "Refresh Tokens." |

### LLM Implementation Guidance:

1. **Prioritize Service Accounts** for 99% of automation tasks.
2. **Always use List of Lists** (`[[row1], [row2]]`) for updates to avoid "Value must be 2D array" errors.
3. **Wrap calls** in a decorator or try/except block specifically catching `gspread.exceptions.APIError` for 429 handling.

