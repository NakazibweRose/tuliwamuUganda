# Deployment & Africa's Talking configuration

Recommended setup: **backend + PostgreSQL on Render**, **frontend on Vercel or Netlify**. Any host with
Python 3.12, PostgreSQL and HTTPS will work.

## 1. Backend on Render

1. Push this repository to GitHub.
2. In Render, choose **New → Blueprint** and select the repository. `render.yaml` creates `tuliwamu-api` and the managed PostgreSQL database `tuliwamu-db`.
3. Fill in the variables marked `sync: false`:
   * `CORS_ALLOWED_ORIGINS`, `CSRF_TRUSTED_ORIGINS`, `FRONTEND_URL` — your frontend URL, e.g. `https://tuliwamu.vercel.app`
   * `FIELD_ENCRYPTION_KEY` — generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`. Keep a secure copy: **without it, encrypted fields cannot be read.**
   * `AFRICASTALKING_API_KEY` — leave empty to use the mock SMS provider.
4. For a demo environment, set `SEED_DEMO_DATA=true` for the first deploy, then remove it. Alternatively, run `python manage.py seed_demo --reset` from the Render shell. **Never seed a production database.**
5. Add Render Cron Jobs (same repository, `rootDir: backend`):

| Schedule | Command |
|---|---|
| hourly | `python manage.py send_reminders` |
| every 15 min | `python manage.py process_sms_queue` |
| every 10 min | `python manage.py purge_ussd_sessions` |

Because the frontend and API are on different sites, the refresh cookie needs `REFRESH_COOKIE_SAMESITE=None`
and `REFRESH_COOKIE_SECURE=True` (already set in `render.yaml`). If you serve both from one domain
(e.g. `app.example.org` and `app.example.org/api`), use `Lax` instead.

Optional: set `REDIS_URL` so rate limits and USSD counters are shared across workers.

## 2. Frontend on Vercel or Netlify

* Root directory: `frontend`. Build: `npm run build`. Output: `dist`.
* Environment variable: `VITE_API_BASE_URL=https://<your-api>.onrender.com`
* `vercel.json` (Vercel) and `public/_redirects` (Netlify) handle single-page-app routing and add security headers.

## 3. Africa's Talking

The platform talks to Africa's Talking only from Django. Credentials never reach the browser.

### Environment variables

```
AFRICASTALKING_USERNAME=sandbox            # your app username in production
AFRICASTALKING_API_KEY=...                 # from the AT dashboard (Settings → API Key)
AFRICASTALKING_ENVIRONMENT=sandbox         # or production
AFRICASTALKING_USSD_SERVICE_CODE=*384*1234#
AFRICASTALKING_USSD_CALLBACK_URL=https://<api>/api/communications/ussd/callback/?token=<CALLBACK_TOKEN>
AFRICASTALKING_USSD_EVENT_URL=https://<api>/api/communications/ussd/events/?token=<CALLBACK_TOKEN>
AFRICASTALKING_SMS_SENDER_ID=              # approved alphanumeric sender ID, if you have one
AFRICASTALKING_CALLBACK_TOKEN=<random>     # appended to callback URLs; requests without it are rejected
```

When `AFRICASTALKING_API_KEY` is set, `SMS_PROVIDER` defaults to `africastalking`. Set `SMS_PROVIDER=mock`
to force the simulator.

### USSD (sandbox)

1. In the AT sandbox, go to **USSD → Create channel** and pick a sandbox service code.
2. Set the callback URL to `https://<api>/api/communications/ussd/callback/?token=<CALLBACK_TOKEN>`.
3. Open the AT **simulator**, enter a test phone number and dial the code. The first screen is the six-language menu.
4. Reports appear under **Anonymous reports** in the dashboard (police and probation accounts).

For production, apply for a dedicated or shared short code through Africa's Talking. In Uganda this
requires approval from the mobile network operators, and possibly zero-rating so reporters are not charged.

### SMS

1. Set the delivery-report callback in the AT dashboard (**SMS → Delivery Reports**) to `https://<api>/api/communications/sms/delivery-callback/?token=<CALLBACK_TOKEN>`.
2. Sandbox messages appear in the AT simulator, not on real phones.
3. Message states in the **SMS delivery** dashboard:
   * `SIMULATED` — mock provider; nothing was sent
   * `SUBMITTED` — AT accepted the request; not yet delivered
   * `DELIVERED` — delivery report confirmed delivery
   * `FAILED` — rejected or failed; retried up to 3 times by `process_sms_queue`
   * `DEFERRED` — waiting for the recipient's quiet hours to end
   * `BLOCKED` — no consent or no safe number; never sent

**The demo seed sets a placeholder safe number (`+256700000001`) only when the mock provider or the AT
sandbox is in use. Never run the seed against a live Africa's Talking account.**

### Swapping providers

Implement a new `SmsProvider.send(phone, message) -> ProviderResult` in `communications/sms/providers.py`
and select it in `get_provider()`. USSD gateways that send cumulative `*`-joined text work with
`UssdEngine.handle()` without changes.

## 4. Production checklist

- [ ] `DJANGO_DEBUG=False`, strong `DJANGO_SECRET_KEY`, dedicated `FIELD_ENCRYPTION_KEY` stored securely
- [ ] HTTPS only; HSTS enabled (automatic when `DEBUG=False`)
- [ ] Managed PostgreSQL with encryption at rest and automated, tested backups
- [ ] Cron jobs configured; `REDIS_URL` set when running more than one worker
- [ ] Africa's Talking callback token set; production short code and sender ID approved
- [ ] Translations reviewed by qualified speakers
- [ ] Legal review against the Data Protection and Privacy Act, 2019 and the Children Act; registration with the Personal Data Protection Office; data protection impact assessment
- [ ] Data-sharing agreements with participating institutions
