# Nashe Designs — Full Website (Flask)

A complete single-seller fashion e-commerce site for **Nashe Designs**: storefront, shopping
cart, one-page checkout with guest checkout, custom design requests, consultation bookings,
order tracking, a Pinterest-style inspiration feed, an admin dashboard, and **Aria** — an AI
shopping assistant powered by the Claude API — plus a floating WhatsApp button.

Design: black & gold luxury palette (Playfair Display + Inter), per the project spec.

---

## 1. What's inside

```
nashe-designs/
├── app.py              # all routes (storefront, checkout, admin, API)
├── models.py            # database models
├── config.py             # settings (reads from environment variables)
├── extensions.py
├── requirements.txt
├── Procfile              # for Render / Railway / Heroku-style hosts
├── .env.example           # copy to .env and fill in your real values
├── static/
│   ├── css/style.css
│   ├── js/main.js
│   └── uploads/            # product photos, inspiration posts, payment proofs (auto-created)
└── templates/
    ├── base.html, index.html, shop.html, product.html, checkout.html, ...
    └── admin/               # admin dashboard templates
```

**No images from the original brief are included yet** — the docx with your dress photos didn't
upload successfully, so the site ships with elegant placeholder tiles. Add real photos any time
via `/admin/products` (product images) and `/admin/posts` (inspiration feed) — no code changes
needed.

---

## 2. Run it locally (test before deploying)

```bash
# 1. Create a virtual environment
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Copy the environment template and edit it
cp .env.example .env
# open .env and fill in ADMIN_PASSWORD, WHATSAPP_NUMBER, payment details, ANTHROPIC_API_KEY, etc.

# 4. Load environment variables (Linux/Mac)
export $(cat .env | xargs)
# Windows PowerShell: Get-Content .env | ForEach-Object { if($_ -match '^([^=]+)=(.*)$'){ [System.Environment]::SetEnvironmentVariable($matches[1],$matches[2]) } }

# 5. Create the database and add demo products (optional but recommended for a first look)
flask --app app seed

# 6. Run the dev server
python app.py
```

Visit **http://localhost:5000** for the storefront and **http://localhost:5000/admin** for the
admin panel (default login: whatever you set as `ADMIN_USERNAME` / `ADMIN_PASSWORD` in `.env`).

---

## 3. Push to GitHub

```bash
cd nashe-designs
git init
git add .
git commit -m "Initial Nashe Designs website"
git branch -M main
git remote add origin https://github.com/<your-username>/nashe-designs.git
git push -u origin main
```

`.gitignore` already excludes `.env`, the SQLite database, and `__pycache__` — your secrets and
local data won't be pushed.

---

## 4. Deploy (free/cheap options that work well for Flask)

### Option A — Render.com (recommended, easiest)
1. Push the repo to GitHub (above).
2. On [render.com](https://render.com) → **New → Web Service** → connect your GitHub repo.
3. Build command: `pip install -r requirements.txt`
4. Start command: `gunicorn app:app`
5. Add all the variables from `.env.example` under **Environment** (set real values —
   `ADMIN_PASSWORD`, `WHATSAPP_NUMBER`, `SECRET_KEY`, `ANTHROPIC_API_KEY`, payment numbers, etc.)
6. Add a free **PostgreSQL** database from Render (New → PostgreSQL) and copy its "Internal
   Database URL" into the `DATABASE_URL` environment variable — this keeps your data safe across
   deploys (SQLite files get wiped on Render's free tier).
7. Deploy. Once live, open `yoursite.onrender.com/admin` and run the seed command from the Render
   shell if you want demo products: `flask --app app seed`.

### Option B — Railway.app
Same idea as Render: connect the GitHub repo, it auto-detects the `Procfile`, add the same
environment variables, attach a Railway PostgreSQL plugin, deploy.

### Option C — PythonAnywhere (good for beginners, free tier available)
1. Upload the project (or clone from GitHub) via their Bash console.
2. Create a virtualenv and `pip install -r requirements.txt`.
3. Set up a new Web App → Flask → point to `app.py`.
4. Set environment variables in the WSGI config file (`os.environ['KEY'] = 'value'` lines) or via
   their "Environment variables" tab if available on your plan.
5. Reload the web app.

---

## 5. Connect real payments and WhatsApp

Nothing here requires code changes — everything reads from environment variables:

| What | Env variable(s) | Notes |
|---|---|---|
| WhatsApp button & chat handoff | `WHATSAPP_NUMBER` | Digits only, country code, no `+` or spaces, e.g. `265991234567` |
| Airtel Money / TNM Mpamba | `AIRTEL_MONEY_NUMBER`, `TNM_MPAMBA_NUMBER` | Shown at checkout + on the confirmation page |
| Bank transfer | `BANK_NAME`, `BANK_ACCOUNT_NAME`, `BANK_ACCOUNT_NUMBER` | |
| Binance Pay / USDT | `BINANCE_PAY_ID`, `USDT_WALLET_ADDRESS` | |
| Visa/Mastercard, PayPal | `STRIPE_*`, `PAYPAL_CLIENT_ID` | These are currently placeholders — the checkout page shows a "we'll follow up with a secure link" message. Wiring up live Stripe/PayPal checkout is a follow-up step once you have merchant accounts; ask and I can build that flow in. |

The current flow for **all** payment methods: customer places the order → sees payment
instructions on the confirmation page → pays and optionally uploads a screenshot at checkout
(or sends it on WhatsApp) → you confirm the payment and move the order to "Payment Confirmed" in
`/admin/orders`.

---

## 6. Turn on the AI chatbot (Aria)

1. Get an API key from [console.anthropic.com](https://console.anthropic.com).
2. Set `ANTHROPIC_API_KEY` in your environment variables (locally in `.env`, or in your host's
   dashboard).
3. That's it — Aria will start answering using live product/category info from your database.
   Without a key, Aria politely points customers to WhatsApp instead of erroring out.

---

## 7. Day-to-day admin tasks

All at `/admin` (login required):

- **Products** — add/edit/delete, upload main + gallery images, mark Trending/Featured, set stock.
- **Orders** — view, see uploaded payment proof, move through Pending → Payment Confirmed →
  In Production → Shipped → Delivered.
- **Custom Requests** — everything submitted from the "Request Custom Design" form.
- **Bookings** — consultation requests; approve/reject/reschedule.
- **Inspiration Feed** — post images/videos with captions & hashtags, pin featured looks, link a
  post to a product.
- **Reviews** — approve reviews before they show on the homepage.

---

## 8. Next steps / things worth doing before a real launch

- Replace placeholder product tiles with real photography (once you re-send the docx, or shoot
  new photos).
- Set a strong, unique `SECRET_KEY` and `ADMIN_PASSWORD` in production — never use the defaults.
- Move off SQLite to PostgreSQL for anything beyond a quick demo (see Render instructions above).
- If you want live card/PayPal processing instead of the "we'll follow up" placeholder, let me
  know and I'll wire up Stripe Checkout or PayPal — needs your merchant account credentials.
- Consider adding HTTPS (automatic on Render/Railway) and a custom domain.
