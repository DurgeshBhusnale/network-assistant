# Go-live credentials: step-by-step

How to get every external credential the app needs, and where each value goes. Work through it in the order below; each section ends with a check that proves it works.

Dashboards change their menus often. If a label here doesn't match what you see, look for the nearest equivalent; the values you need stay the same.

## 0. Before you start

| Need | Why | When |
|---|---|---|
| A domain you control (e.g. `yourapp.in`) | Email sending (Resend), Meta app review, Razorpay activation | Before Resend and before going live |
| A public HTTPS URL for the API | Meta and Razorpay must reach the webhooks | Staging deploy, or a tunnel for dev testing (below) |
| Public pages: Privacy policy, Terms, Refund & cancellation, Contact us | Meta app Live mode and Razorpay activation check them | Before live mode (placeholder text exists at `/privacy` and `/terms`; refund and contact pages still need writing) |
| Business details: legal name, PAN, bank account, address (GSTIN if registered) | Razorpay KYC, Meta business verification | Before live payments / production WhatsApp number |

**Where values go**

- Dev: the root `.env` (git-ignored). Restart `pnpm dev` after changing it.
- Staging / production: the host's secret manager, never in a file in the repo.
- Values starting `NEXT_PUBLIC_` are built into the web app: rebuild the web app after changing them.
- Use test/sandbox credentials for dev and staging; live credentials only in production.
- Never paste secrets into chat, tickets or commits.

**Tunnel for dev webhooks** (only while there is no staging API): install `cloudflared`, then run `cloudflared tunnel --url http://localhost:8000`. It prints an `https://<random>.trycloudflare.com` URL that forwards to your local API. The URL changes every run, so update the webhook URLs in Meta and Razorpay each time. Stop the tunnel when you're done.

---

## 1. Unsubscribe secret (2 minutes)

Signs the one-click unsubscribe links in the weekly email.

1. Generate a random value:
   ```powershell
   cd apps/api
   uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Put it in `.env`: `UNSUBSCRIBE_SECRET=<value>`.
3. Use a **different** value per environment (dev, staging, production).
4. Don't change it once emails have gone out: links in old emails stop working.

Check: none needed; it's used when the first digest email is sent (section 4).

---

## 2. Web push keys (VAPID) (2 minutes)

Lets the installed app show notifications. No account needed.

1. Generate a key pair:
   ```powershell
   cd apps/api
   uv run python -m app.vapid
   ```
   It prints three lines: `VAPID_PUBLIC_KEY`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY` (same value) and `VAPID_PRIVATE_KEY`.
2. Copy all three into `.env`, and set `VAPID_SUBJECT=mailto:<an email you read>` (push services use it to contact you about problems).
3. Generate a separate pair per environment. Keep the private key secret. Changing keys later means every user has to turn notifications on again.
4. Rebuild the web app (the public key is a `NEXT_PUBLIC_` value) and restart the API and worker.

Check: install the app on your phone (production build), open **Settings → Reminders**, turn on **Notifications on this phone**, allow the prompt. You should see the toggle stay on. A push arrives at your nudge time if you're on a paid plan, or with the weekly digest if you're on the free plan.

---

## 3. Razorpay (test mode: 15 minutes; live: days, after KYC)

### 3a. Test mode (do this now)

1. Sign up at **dashboard.razorpay.com** with the business email.
2. Switch the dashboard to **Test Mode** (toggle at the top).
3. **Account & Settings → API Keys → Generate Test Key.** Copy the **Key Id** (`rzp_test_…`) and the **Key Secret**. The secret is shown only once; if you lose it, regenerate.
4. **Account & Settings → Webhooks → Add New Webhook:**
   - Webhook URL: `<public API URL>/v1/webhooks/razorpay` (the tunnel URL in dev, the staging API later)
   - Secret: generate one with the command from section 1 and paste it here
   - Active events: tick `payment.captured`, `order.paid` and `refund.processed`
   - Save.
5. Put in `.env`:
   ```
   RAZORPAY_KEY_ID=rzp_test_...
   RAZORPAY_KEY_SECRET=...
   RAZORPAY_WEBHOOK_SECRET=<the secret from step 4>
   NEXT_PUBLIC_RAZORPAY_KEY_ID=rzp_test_...   # same as RAZORPAY_KEY_ID; the key id is public
   ```
6. Rebuild the web app and restart the API. With keys present, the dev "simulate payment" checkout switches off and real Razorpay Checkout opens.

Check: in the app open **Upgrade → Career Sprint**. Razorpay Checkout opens. Pay with UPI ID `success@razorpay` (test mode) or a Razorpay test card. Within a few seconds the screen shows the Sprint plan and **Settings → Your plan** shows days left. In the Razorpay dashboard, **Webhooks** shows the delivery with status 200. If the plan doesn't change, the webhook isn't reaching the API: check the URL, the tunnel, and that the secret matches.

### 3b. Live mode (before taking real money)

1. **Activate the account:** fill the activation form (business type, PAN, bank account, business address, website/app URL). Razorpay checks the website for Privacy, Terms, Refund & cancellation, Contact us and pricing; publish those pages first.
2. Wait for approval (usually a few working days; they may ask for documents).
3. Switch to **Live Mode**, generate **live** API keys, add the same webhook (live mode has its own webhook list and secret).
4. Put the live values only in the production secret manager.
5. Test once with a real small payment and refund it from the dashboard; check the plan turns on and then off again.

---

## 4. Resend (email) (30 minutes, plus DNS wait)

Sends the weekly digest. The same account can also send the sign-in code emails (section 6.3).

1. Sign up at **resend.com**.
2. **Domains → Add Domain.** Use a subdomain such as `mail.yourapp.in` (keeps the main domain's email reputation separate). Pick the region closest to India if offered.
3. Resend shows DNS records (an MX and a TXT record for SPF on a sending subdomain, and a TXT record for DKIM). Add each one exactly at your DNS provider (where you bought the domain, or Cloudflare). Also add a DMARC record if you don't have one: TXT `_dmarc.yourapp.in` = `v=DMARC1; p=none; rua=mailto:<you>`.
4. Back in Resend, click **Verify**. DNS can take from minutes to a few hours.
5. **API Keys → Create API Key:** permission **Sending access**, restricted to your domain. Copy it (shown once).
6. Put in `.env`:
   ```
   RESEND_API_KEY=re_...
   EMAIL_FROM="[App name] <hello@mail.yourapp.in>"
   ```
   The address must be on the verified domain.
7. Restart the API and worker.

Check: the free-plan digest goes out at `DIGEST_WEEKDAY` / `DIGEST_HOUR` (default Monday 9:00, user's local time). To test sooner, temporarily set those two values to the current weekday (0 = Monday) and hour, restart the worker, and wait up to 15 minutes. You should get the email, and its unsubscribe link should show "You're unsubscribed". Put the values back afterwards.

---

## 5. Meta WhatsApp Cloud API (test number: 1 hour; production: 1–3 weeks)

### 5a. App and test number (do this now)

1. Create (or use) a **Meta Business portfolio** at **business.facebook.com** with the business's legal name.
2. At **developers.facebook.com → My Apps → Create App**: choose the use case for WhatsApp / type **Business**, and link it to the business portfolio.
3. In the app, add the **WhatsApp** product. Open **WhatsApp → API Setup**. Meta gives you a free **test number**.
4. From API Setup copy:
   - **Phone number ID** → `WA_PHONE_NUMBER_ID`
   - **WhatsApp Business Account ID** → `WA_BUSINESS_ACCOUNT_ID`
   - The **Graph API version** in the sample request (e.g. `v2X.0`) → `WA_GRAPH_VERSION`
5. Under **To**, add your own phone number as a test recipient and confirm it with the code WhatsApp sends you. The test number can only message up to 5 verified recipients.
6. **App settings → Basic → App secret → Show.** Copy it → `WA_APP_SECRET` (used to check webhook signatures).
7. Make up a verify token (section 1 command) → `WA_VERIFY_TOKEN`.
8. **Permanent access token** (the token on API Setup expires in 24 hours):
   1. **business.facebook.com → Settings → Users → System users → Add**: name it (e.g. `api`), role **Admin**.
   2. **Assign assets**: add the app (full control) and the WhatsApp account (full control).
   3. **Generate token**: pick the app, expiry **Never**, permissions `whatsapp_business_messaging` and `whatsapp_business_management`. Copy it → `WA_ACCESS_TOKEN`.
9. Set `WA_DISPLAY_NUMBER` to the WhatsApp number users will message, digits only with country code (for the test number, the number shown on API Setup).
10. **Webhook:** start the tunnel (section 0) or use the staging API, restart the API with the values above, then in **WhatsApp → Configuration → Webhook → Edit**:
    - Callback URL: `<public API URL>/v1/webhooks/whatsapp`
    - Verify token: the `WA_VERIFY_TOKEN` value
    - **Verify and save** (our API answers Meta's check). Then under **Webhook fields**, subscribe to **messages**.

Check: in the app open **Settings → WhatsApp assistant → Link WhatsApp**. WhatsApp opens with a `START <code>` message; send it. You should get a "linked" reply, and Settings shows **Linked to …1234**. Send a note like "Met Priya from Zoho at a meetup": it shows up for review in the app. Send `STOP`: Settings shows you opted out.

Leave `WA_BRIEFS_ENABLED=false` until the `daily_brief_v1` template is approved (5c).

### 5b. Production number (before beta)

1. **Business verification:** business.facebook.com → **Settings → Security Center → Start verification**. Upload documents (registration certificate, GST or utility bill matching the legal name and address). Takes a few days to two weeks.
2. **Add a real number:** WhatsApp Manager → **Phone numbers → Add phone number**. Use a number that is not registered on any WhatsApp app (or delete it from the app first). Verify by SMS or call.
3. **Display name:** set the app's name; Meta reviews it against your website and brand.
4. **Payment method:** WhatsApp Manager → add a card for message charges (we only start conversations with paid users, so costs stay small).
5. **App Live mode:** in the developer app, fill in Privacy policy URL, Terms URL, app icon and category, then switch the app to **Live**.
6. Point `WA_PHONE_NUMBER_ID` and `WA_DISPLAY_NUMBER` at the new number in production, keep the same webhook settings, and re-run the check from 5a.

### 5c. Message templates (needed for the daily brief)

WhatsApp Manager → **Message templates → Create template**, category **Utility**, language **English**, then create each of these exactly (names, variables and buttons must match what the code sends):

| Name | Body | Buttons |
|---|---|---|
| `daily_brief_v1` | `Good morning {{1}}. Today's people to reach out to:` then lines `1. {{2}}`, `2. {{3}}`, `3. {{4}}`, then `Tap Show drafts to get your messages ready.` | Quick reply: `Show drafts`, `Snooze today` |
| `sprint_reminder_v1` | `Your Career Sprint has {{1}} days left. Referrals so far: {{2}}.` | URL button `Open app` → `<APP_BASE_URL>/today` |
| `capture_ready_v1` | `Saved your note. I found {{1}} people for you to check.` | URL button `Review in app` → `<APP_BASE_URL>/today` |

Sample values for review: {{1}} Rohan; {{2}} Ananya Kulkarni — Target company; {{3}} Vikram Joshi — Birthday today; {{4}} Priya Nair — Met at eChai.

Approval usually takes minutes to a day. If one is rejected, the reason is shown in WhatsApp Manager; adjust the wording, keep the same variables, and resubmit. Once `daily_brief_v1` is approved, set `WA_BRIEFS_ENABLED=true` and `WA_TEMPLATE_LANGUAGE=en`.

---

## 6. Supabase sign-in settings (for every environment)

Needed before anyone can sign in. Do it for the dev project now and repeat for staging and production with their own URLs.

### 6.1 URLs

**Authentication → URL Configuration**

- Site URL: `http://localhost:3000` (dev); later `https://<staging or production web URL>`
- Redirect URLs: add `http://localhost:3000/auth/callback`; later the staging and production `/auth/callback` URLs

### 6.2 Google sign-in

1. **console.cloud.google.com** → create a project (e.g. `yourapp-auth`).
2. **APIs & Services → OAuth consent screen** (also shown as **Google Auth Platform**): user type **External**; app name, support email, logo optional; app domain and authorized domain: your domain and `supabase.co`; scopes `openid`, `email`, `profile` (the defaults). While the app is in **Testing**, add your Google accounts as **test users**. Publish it before beta.
3. **Credentials → Create credentials → OAuth client ID**: type **Web application**.
   - Authorized JavaScript origins: `http://localhost:3000` (+ staging/production web URLs)
   - Authorized redirect URI: `https://<project-ref>.supabase.co/auth/v1/callback` (the exact value is shown on the Supabase Google provider page)
4. Copy the **Client ID** and **Client secret**.
5. Supabase: **Authentication → Sign In / Providers → Google** → enable, paste both, save.

Check: on `/sign-in` tap **Continue with Google**, choose a test-user account, and you land on the consents screen (new user) or Today.

### 6.3 Email sign-in code

1. **Authentication → Emails → Templates → Magic Link**: make sure the body includes `{{ .Token }}` so the email shows the 6-digit code (the link in it also works). Example: `Your sign-in code is {{ .Token }}. Or tap this link: {{ .ConfirmationURL }}`.
2. **Use your own email sender.** Supabase's built-in sender is only for trying things out: it is heavily rate-limited and only delivers to members of your Supabase team. Under **Authentication → Emails → SMTP Settings**, enable custom SMTP with Resend (section 4):
   - Host `smtp.resend.com`, port `465`, username `resend`, password: a Resend API key
   - Sender email: an address on the verified domain; sender name: the app name
3. Optional: under **Authentication → Rate Limits**, review the email limits for beta.

Check: on `/sign-in` enter an email that is not on your Supabase team, tap **Email me a sign-in code**, and the code arrives from your domain within a minute.

---

## 7. Final checklist

| Value | Dev `.env` | Staging | Production |
|---|---|---|---|
| `UNSUBSCRIBE_SECRET` | ☐ | ☐ | ☐ |
| `VAPID_*`, `NEXT_PUBLIC_VAPID_PUBLIC_KEY` | ☐ | ☐ | ☐ |
| `RAZORPAY_*`, `NEXT_PUBLIC_RAZORPAY_KEY_ID` | ☐ test | ☐ test | ☐ live |
| `RESEND_API_KEY`, `EMAIL_FROM` | ☐ | ☐ | ☐ |
| `WA_*` | ☐ test number | ☐ test number | ☐ production number |
| Supabase URLs, Google provider, SMTP | ☐ | ☐ | ☐ |

After filling a column: restart the API and worker, rebuild the web app, and run each section's check.
