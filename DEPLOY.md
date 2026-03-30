# DSTAIR — Deployment Guide

Complete step-by-step deployment for all hosting options.
Pick your section and follow it top-to-bottom.

---

## Before You Deploy (All Platforms)

### 1. Generate a secure SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output — you'll need it in your `.env`.

### 2. Prepare your .env file

Duplicate `.env.example` → `.env` and fill in real values:

```
SECRET_KEY=<paste the key you generated above>
FLASK_ENV=production
DATABASE_URI=sqlite:///database.db
GROQ_API_KEY=<your Groq key>
```

> **Never commit `.env` to Git.** It's already in `.gitignore`.

---

## Option A — GoDaddy Shared Hosting (cPanel)

> Works on GoDaddy Economy / Deluxe / Ultimate Web Hosting plans.

### Step 1 — Log into cPanel
Go to: **GoDaddy → My Products → Web Hosting → Manage → cPanel**

### Step 2 — Create a Python App
1. In cPanel, find **"Setup Python App"** (under Software section)
2. Click **"Create Application"**
3. Fill in:
   - **Python version**: `3.11` (or highest available)
   - **Application root**: `dstair` (this will be `/home/USERNAME/dstair`)
   - **Application URL**: `/` (or a subdirectory if you want)
   - **Application startup file**: `passenger_wsgi.py`
   - **Application Entry point**: `application`
4. Click **Create**

### Step 3 — Upload your files
In cPanel File Manager (or via FTP/SSH):
1. Navigate to the folder cPanel created (e.g. `/home/USERNAME/dstair/`)
2. Upload **all project files** there (everything in `main-dstair/`)

Your folder should look like:
```
/home/USERNAME/dstair/
    app.py
    wsgi.py
    passenger_wsgi.py
    config.py
    extensions.py
    run.py
    requirements.txt
    .env                  ← create this manually
    static/
    templates/
    routes/
    models/
    ...
```

### Step 4 — Create your .env file
In cPanel File Manager, create a new file named `.env` in the app folder with:
```
SECRET_KEY=your-generated-key-here
FLASK_ENV=production
DATABASE_URI=sqlite:///database.db
GROQ_API_KEY=your-groq-key-here
```

### Step 5 — Install dependencies
Back in **Setup Python App**, click on your app → **"Open Terminal"** (or use cPanel Terminal):

```bash
source /home/USERNAME/virtualenv/dstair/3.11/bin/activate
cd ~/dstair
pip install -r requirements.txt
```

### Step 6 — Initialize the database
```bash
# Still in the activated virtualenv:
export FLASK_ENV=production
python -c "from app import create_app; from utils.db_init import ensure_database_initialized; app = create_app(); app.app_context().push(); ensure_database_initialized(force_seed=True)"
```

### Step 7 — Restart the app
In cPanel **Setup Python App** → click your app → **Restart**.

### Step 8 — Test
Visit your domain. If you see a 500 error, check:
- cPanel → Logs → Error Log
- Make sure `.env` has a valid `SECRET_KEY`

---

## Option B — GoDaddy VPS (Linux Server)

> Works on GoDaddy VPS plans with root SSH access.

### Step 1 — SSH into your server
```bash
ssh root@YOUR_SERVER_IP
```

### Step 2 — Upload your project files
From your local machine:
```bash
scp -r ./main-dstair/* root@YOUR_SERVER_IP:/tmp/dstair_upload/
```

Or use FileZilla (SFTP, port 22).

### Step 3 — Run the setup script
On the server:
```bash
# First, create the app directory and move files
mkdir -p /home/dstair/app
cp -r /tmp/dstair_upload/* /home/dstair/app/

# Edit the domain in setup script
nano /home/dstair/app/deploy/setup_vps.sh
# Change: DOMAIN="YOUR_DOMAIN" → DOMAIN="yourdomain.com"

# Run it
chmod +x /home/dstair/app/deploy/setup_vps.sh
bash /home/dstair/app/deploy/setup_vps.sh
```

### Step 4 — Create .env on the server
```bash
nano /home/dstair/app/.env
```
Add:
```
SECRET_KEY=your-generated-key-here
FLASK_ENV=production
DATABASE_URI=sqlite:////home/dstair/app/instance/database.db
GROQ_API_KEY=your-groq-key-here
```

### Step 5 — Initialize the database
```bash
cd /home/dstair/app
source venv/bin/activate
export FLASK_ENV=production
python -c "from app import create_app; from utils.db_init import ensure_database_initialized; app = create_app(); app.app_context().push(); ensure_database_initialized(force_seed=True)"
```

### Step 6 — Start the app
```bash
sudo systemctl start dstair
sudo systemctl status dstair   # should show: active (running)
```

### Step 7 — Get free SSL (HTTPS)
```bash
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```
Follow the prompts. Certbot auto-renews every 90 days.

### Step 8 — Point your GoDaddy domain to this server
In GoDaddy DNS settings:
- Add an **A record**: `@` → `YOUR_SERVER_IP`
- Add an **A record**: `www` → `YOUR_SERVER_IP`
- TTL: 600

---

## Option C — Railway (Easiest Cloud Option)

> Free tier available. No server management needed.

### Step 1 — Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/dstair.git
git push -u origin main
```

### Step 2 — Deploy on Railway
1. Go to [railway.app](https://railway.app) → New Project → Deploy from GitHub
2. Select your repo
3. Railway auto-detects the `Procfile` and deploys

### Step 3 — Set environment variables
In Railway dashboard → Variables:
```
SECRET_KEY = your-generated-key-here
FLASK_ENV  = production
GROQ_API_KEY = your-groq-key-here
```

### Step 4 — Add your domain
Railway dashboard → Settings → Domains → Add custom domain → enter your GoDaddy domain.

Then in GoDaddy DNS, add a CNAME record:
- `@` or `www` → the Railway-provided URL

---

## Option D — Render

Similar to Railway.

1. Push to GitHub (same as Option C Step 1)
2. Go to [render.com](https://render.com) → New Web Service → Connect GitHub
3. Set:
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app --workers 2 --threads 2 --timeout 120`
4. Add environment variables (same as Railway Step 3)
5. Add custom domain in Render settings

---

## Updating the App (After First Deploy)

### VPS
```bash
# Upload new files via SCP or Git pull
cd /home/dstair/app
git pull   # if you set up git on the server
sudo systemctl restart dstair
```

### cPanel
Upload changed files via File Manager/FTP, then restart in Setup Python App.

### Railway / Render
Just `git push` — they auto-redeploy.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `RuntimeError: FATAL: SECRET_KEY contains insecure default` | Set a real `SECRET_KEY` in `.env` |
| 500 error on first visit | Run the database initialization command (Step 5/6) |
| Static files not loading on VPS | Check nginx `alias /home/dstair/app/static/` path |
| `ModuleNotFoundError` on cPanel | Run `pip install -r requirements.txt` in the activated virtualenv |
| App crashes after server reboot | `sudo systemctl enable dstair` (VPS only) |
| CSRF errors after deploy | Ensure `SECRET_KEY` is set and consistent |

---

## File Reference

| File | Purpose |
|------|---------|
| `wsgi.py` | Universal WSGI entry — used by Gunicorn, Passenger, Railway, Render |
| `passenger_wsgi.py` | Specific to GoDaddy cPanel Passenger |
| `Procfile` | Railway / Render / Heroku process definition |
| `runtime.txt` | Python version pin (Railway / Render) |
| `deploy/nginx.conf` | Nginx reverse proxy config (VPS) |
| `deploy/dstair.service` | systemd service unit (VPS) |
| `deploy/setup_vps.sh` | Automated VPS first-time setup script |
