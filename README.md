# QR Login for Home Assistant

Log in to Home Assistant on a device that's hard to type on, like a car
dashboard, a TV, or a kiosk. The device opens `/qr-login` and shows a QR
code. You scan it with a phone that's already signed in, check that the
code on screen matches, pick which user to sign in as, and tap Approve.
The device is logged in right away.

It was built for the browser in Tesla cars, but it works on anything with
a modern browser.

## How the login stays safe

- No tokens or secrets are stored ahead of time. A token is only created
  the moment someone approves the login, and it's handed to the device once.
- Codes are random, single use, and expire after 60 seconds (you can set
  this anywhere from 30 to 300).
- Approval goes over Home Assistant's authenticated connection, so the
  approver is whoever is actually signed in on the phone. It can't be faked.
- Admins can always approve. A regular user can't approve anything, even
  their own login, unless you add them to the allowlist in the options. A
  user on the allowlist can only sign a device in as themselves. Signing in
  as a different user needs an admin, and you can turn that off completely.
  The owner account can never be signed in this way.
- Each approval sends a `qr_login_approved` event and a notification that
  says who approved it and for which user.
- The new token shows up in that user's profile as "QR Login (approved by
  ...)". Delete it there to end the session on the device.
- The public login page is rate limited per IP, and there's a cap on how
  many logins can be pending at once.

## Install

1. In HACS, add `https://github.com/archyesty/HA-QR-Login` as a custom
   repository (type: Integration). Or copy `custom_components/qr_login`
   into your config folder by hand.
2. Restart Home Assistant, then add the "QR Login" integration.
3. It works out of the box on your internal address, like
   `http://homeassistant.local:8123/qr-login`. To also log in from outside
   your network, set your external URL (Settings → System → Network) and
   open the page on that HTTPS address instead. The login is tied to
   whichever address the device actually uses.

## Using it

1. On the device, open `<your HA address>/qr-login`. Internal or external
   both work; the phone that approves just needs to be signed in on that
   same address.
2. Scan the QR code with your signed-in phone.
3. Check the 6-character code matches, pick the user, and tap Approve.

## Options

- How long a code stays valid, in seconds.
- Whether admins can sign a device in as another user.
- Which non-admin users are allowed to approve their own logins.
