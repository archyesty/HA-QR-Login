# QR Login for Home Assistant

Device-code style login: a car, TV, or kiosk opens `/qr-login` and shows a QR code. A phone that's already signed in to Home Assistant scans it, verifies the on-screen code, picks which user to sign the device in as, and approves. The device logs in instantly.

Built for the Tesla browser; works on anything with a modern browser.

## Security model
- **Nothing exists before approval.** No pre-created tokens, no secrets at rest. Credentials are minted at the moment an authenticated user approves, and handed over exactly once.
- Codes are 128-bit random, single-use, expire in 60s (configurable 30–300s).
- Approval happens over Home Assistant's authenticated WebSocket — the approver's identity comes from their session and cannot be spoofed.
- **Admins can always approve. Non-admin users can approve nothing — not even for themselves — unless explicitly allowlisted in the integration options.** Allowlisted non-admins can only sign a device in as themselves. Cross-user sign-in requires an admin approver and can be disabled entirely in options. The owner account can never be a cross-user target.
- Every approval fires a `qr_login_approved` event and a persistent notification naming approver and target.
- Minted tokens appear in the target user's profile as "QR Login (approved by …)" — revoke there anytime to kill the device session.
- Unauthenticated endpoints are rate-limited per IP; pending sessions are globally capped.

## Install
1. HACS → custom repository → this repo (Integration), or copy `custom_components/qr_login` into your config.
2. Restart HA, add the "QR Login" integration.
3. Works out of the box on your internal address (e.g. `http://homeassistant.local:8123/qr-login`). To also sign in from outside your network, set your external URL (Settings → System → Network) and open the page on that HTTPS domain instead — the login is tied to whichever address the device uses.

## Use
1. On the device: open `<the address you use for HA>/qr-login` — internal or external both work; the phone approving just needs to be signed in on that same address.
2. Scan the QR with your signed-in phone.
3. Verify the 6-character code matches, choose the user, Approve.

## Options
- Code TTL (seconds)
- Allow cross-user sign-in (admins only)
- Allowlist of non-admin users permitted to approve (self only)
