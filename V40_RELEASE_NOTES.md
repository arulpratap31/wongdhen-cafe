# Wongdhen Café V40 — Dedicated Role Portals

## What changed

- `/admin` is now a neutral **team sign-in hub**, listing owner, management, reception, kitchen and content portals.
- Dedicated, refreshable and bookmarkable **owner** pages: `/owner`, `/owner/finance`, `/owner/growth`, `/owner/customers`, `/owner/team`, `/owner/editorial`, `/owner/reservations`, `/owner/menu`, `/owner/audit`.
- Dedicated **manager** pages: `/manager`, `/manager/daily`, `/manager/reservations`, `/manager/calendar`, `/manager/kitchen`, `/manager/menu`, `/manager/inbox`, `/manager/queue`.
- Distinct **staff workspaces**: `/staff/reservations`, `/staff/kitchen`, `/staff/content`, with respective booking/calendar/queue, kitchen/order and menu/photo/upload subpages.
- Navigation is role-specific, and updating a section updates the browser URL so staff can bookmark it and use Back/Forward.
- A new contextual top navigation, more polished role-specific visual identity and revised portal sign-in copy.
- Sign-in at `/admin` redirects to the right personal portal; neither manipulating the URL nor changing navigation controls can increase backend permissions.
- Owner finance and registered-customer records remain owner-only. Financial ledger is manually recorded and is not verified POS revenue.
- Kitchen and front-of-house tools retain the restricted data fields and role-based access introduced in V38.
- Staff credentials are created and deactivated by the owner in `/owner/team`.

## Tests

- `tests/test_v40_portals.py` checks all 29 new page routes when anonymous, correct role pages after login, wrong-role access rejection, owner data isolation, employee deactivation and new static assets.
- Existing V38/V39 backend permission tests are retained.
- Frontend files are syntax-checked and the ZIP is checked for extractability.

## Operational limits

- This is a runnable local-staging release, not a claim of complete production certification. Validate real HTTPS, hosting, backups, cookies, database configuration and access policies before public launch.
- Staff roles available in this build: manager, booking_staff, kitchen_staff, content_editor. New roles require explicitly defined permissions and additional tests.
- `/account` is a separate customer-login experience, not an employee portal. Real Google Sign-In still requires the owner's OAuth credentials and registered callback.
- V39 public pages, reservation logic, media library and backend operations remain in this package.
