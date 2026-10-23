# Wongdhen Café V40 — Dedicated Role Portals

**Latest release:** [V40_RELEASE_NOTES.md](V40_RELEASE_NOTES.md). Dedicated owner, manager, reception, kitchen and content URLs, plus the V39 visit guide, Growth Studio and manager checklist. All V38 role-security and financial provenance distinctions remain in effect.

# Wongdhen Café V40 — Dedicated Role Portals

A single FastAPI hospitality website with original licensed café photo assets, the full 16-page original menu, customer accounts and optional Google sign-in, bookings/queue/order modules, V37 photographic experiences, and **V38's new role-separated management suites**.

## Windows local installation

1. Extract the single `Wongdhen-Cafe-V40-Dedicated-Role-Portals-Clean.zip`. Open the `wongdhen-cafe` folder.
2. Copy `.env.example` to `.env` in the same folder.
3. Set `ADMIN_USERNAME`, a strong unique `ADMIN_PASSWORD`, and a newly generated `SESSION_SECRET` (minimum 40 characters) in `.env`. To generate a secret using Windows CMD/PowerShell: `py -c "import secrets; print(secrets.token_hex(32))"`.
4. Double-click **`START_V40_WINDOWS.cmd`**. On first launch it creates an isolated `.venv` and installs the packages in `requirements.txt`, which requires internet connectivity. Python 3.11+ is recommended.
5. Visit **http://127.0.0.1:8765/** to view the café; **http://127.0.0.1:8765/admin** to sign in as owner, manager, or assigned staff; **http://127.0.0.1:8765/account** for customer accounts. The team sign-in hub redirects each employee into a separate role-specific URL. Direct role URLs also support private sign-in.

The launcher uses only **127.0.0.1:8765** for local development. Stop any earlier V36/V37 server still using this port before starting V40. The launcher refuses `ENVIRONMENT=production` and does not host a public internet site.

### Three distinct role-based management workspaces

| Role | Visible functions | Protected information |
|---|---|---|
| **Owner** (`ADMIN_USERNAME` / `ADMIN_PASSWORD`) | Executive dashboard, owner-only revenue/expense ledger, recorded net position, registered customer directory, business analysis, staffing controls, audit and settings, guest content moderation; can also oversee service | Exclusive access to owner finance and registered customer-account directory |
| **Manager** | Manager dashboard, pending bookings, calendar, walk-ins, kitchen operations, guest correspondence, menu quality and operational counts | Cannot see owner finance ledger, owner business statements, registered account directory or staff administration |
| **Reservations staff** | Assigned bookings, booking calendar, walk-in and waitlist tools | No financial reports, employee administration or customer-account directory |
| **Kitchen staff** | Order queue and fulfilment transitions | Order API omits name/contact, notes, item monetary values and totals; no finance/customer directory |
| **Content staff** | Menu and image content/editorial tools per existing server permissions | No finances, reservations, customer-account directory or staffing controls |

The owner creates/updates staff credentials under **Team access**. Each employee has an individual username/password with PBKDF2 hashing, scoped role and revocable session. The owner can deactivate or reassign roles; updates immediately revoke old staff sessions. Browser tab visibility is only the presentation layer. Every protected operation is checked again on the **server**. Changes require CSRF protection.

### Owner-only finance: important accounting distinction

`/owner/finance` → **Sales & finances** is a **manual entry ledger**. An owner records reconciled revenue (dine-in, takeaway, other income) and expenses (ingredients, payroll, rent, etc.), with optional receipt reference. The page then calculates **revenue minus recorded expenses**, displays recent figures and offers an audited delete action.

**Do not claim accounting profit or POS-integrated sales.** Existing online orders are only requests; the system does **not** collect payment online. This release never assumes a placed/fulfilled order was actually paid, and does not invent sales. The owner's manually entered ledger must be reconciled to real POS/bank records to produce meaningful figures. Customer account counts are registrations, not unique visitors or venue footfall. Don't enter a transaction twice.

### Google Sign-In

The existing customer OpenID Connect/OAuth flow remains in the project; it is entirely separate from staff/owner login. To enable real Google sign-in:

1. Create an OAuth **Web application** client in Google Cloud and configure its consent/branding.
2. Register exactly `http://127.0.0.1:8765/api/v24/auth/google/callback` for local development.
3. Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in the private `.env`. Leave `GOOGLE_REDIRECT_URI` blank locally or set it to that exact callback.
4. Restart V40 and complete a real sign-in test via `/account`.

For a public domain, configure a genuine HTTPS URL, register the HTTPS callback with Google and configure deployment secrets. Do not store credentials in the ZIP or publish `.env`.

### Retained interactive café experiences

- `/atelier`: editorial photo presentation, verified spotlight, menu-based meal planner and postcard/mood-sharing tools.
- `/guestbook`: public, permission-based moderated guest notes; *not* automatically verified public reviews.
- `/living-house`: interactive atmospheric treatment of authentic photos, **not** a true property 360 scan.
- `/food-theatre`: published dishes with available verified dish-specific media only.
- `/moments`: digital photographic moodboard.
- `/plan-your-moment`: invitation planner, with real bookings delegated to the actual backend.
- Owner-only editorial admin section: curate a real photograph, update featured text, moderate submitted guest notes and inspect opt-in aggregate engagement events.

### Deployment caveats

This ZIP is a **development/staging deliverable**, not an independently certified fully production-ready payment platform. Verify pricing, ownership and accuracy of menu/imagery, reservations and customer consent. For actual launch you need a managed HTTPS server, production secrets, real backups, data retention rules, monitoring, server-side scaling/rate-limiting and full manual browser/Google OAuth tests. Do not enable payment or claim profit reports without a verified POS/payment feed.

The ZIP intentionally omits caches, compiled Python files, previous-version release notes, live databases, `.env`, `.venv`, and unused archives. Runtime modules with old names (e.g. `v8.py`) are **kept** because V38 imports them. The original café photographs, menu PDF and required runtime manifests remain intact. See `V38_RELEASE_NOTES.md` for the completed audit and test limitations.


## V40: separate staff, manager, and owner URLs

Open `/admin` to choose the right private login, or go directly to a dedicated URL:

| Role | Portal | Main subpages |
|---|---|---|
| Owner | `/owner` | `/owner/finance`, `/owner/growth`, `/owner/customers`, `/owner/team`, `/owner/audit` |
| Manager | `/manager` | `/manager/daily`, `/manager/reservations`, `/manager/calendar`, `/manager/kitchen`, `/manager/inbox` |
| Reception / booking staff | `/staff/reservations` | `/staff/reservations/bookings`, `/staff/reservations/calendar`, `/staff/reservations/waitlist` |
| Kitchen staff | `/staff/kitchen` | `/staff/kitchen/orders` |
| Content staff | `/staff/content` | `/staff/content/menu`, `/staff/content/photos`, `/staff/content/upload` |

The owner creates unique staff accounts in `/owner/team`. No shared staff password is required. Logins from `/admin` redirect each account to its designated portal; a user cannot select another role to gain access. If a manager attempts `/owner/finance`, the server returns HTTP 403; financial and customer API endpoints also enforce owner-only access. Invalid/expired sessions are shown a sign-in form rather than private data. These pages are marked noindex and no-store, and all privileged mutations require CSRF protection.

The navigation also offers dedicated subpage URLs and fallback URLs (`?section=...`) for less frequently used controls. On a fresh browser, direct portal links show the corresponding role's sign-in page. Google customer OAuth (`/account`) is separate from employee/admin authentication.
