# DSTAIR — GoDaddy Deployment Guide

## Deploy from GitHub to GoDaddy cPanel (Shared Hosting)

> **Hosting required:** GoDaddy Linux Web Hosting (Economy / Deluxe / Ultimate).
> These plans include cPanel + Phusion Passenger + Python App support.
> Windows hosting will NOT work — Python apps require Linux.

---

## Overview

The deployment flow is:

```
Your Machine  →  GitHub Repo  →  GoDaddy Server (SSH clone)  →  cPanel Python App
```

The SQLite database (`instance/database.db`) is tracked in the repo, so your
current data ships with the code — no manual seeding needed on the server.

---

## Part 1 — Prepare Your Repo (Do This Once, Locally)

### 1.1 Make sure the database file is tracked

The `.gitignore` already allows `instance/database.db`. Verify it is staged:

```bash
cd main-dstair
git status instance/database.db
```

If it shows **"Untracked"** or is missing, force-add it:

```bash
git add -f instance/database.db
```

> `database.db-shm` and `database.db-wal` (WAL lock files) must NOT be committed.
> The `.gitignore` already excludes them via `instance/*` + `!instance/database.db`.

### 1.2 Commit and push everything

```bash
git add .
git commit -m "chore: prepare for GoDaddy deploy"
git push origin main
```

Make sure your GitHub repo is **public** (or you'll need an SSH deploy key on the server).

---

## Part 2 — GoDaddy cPanel: Create the Python App

### 2.1 Open cPanel

```
GoDaddy Account → My Products → Web Hosting → Manage → cPanel
```

### 2.2 Create the Python App

1. In cPanel, scroll to **Software** → click **"Setup Python App"**
2. Click **"Create Application"**
3. Fill in these exact fields:

   | Field | Value |
   | --- | --- |
   | Python version | `3.11` (pick the highest 3.11.x available) |
   | Application root | `dstair` |
   | Application URL | `/` (root of your domain) |
   | Application startup file | `passenger_wsgi.py` |
   | Application Entry point | `application` |

4. Click **Create**

cPanel will create:

- The folder `/home/YOUR_USERNAME/dstair/`
- A virtualenv at `/home/YOUR_USERNAME/virtualenv/dstair/3.11/`

> Write down `YOUR_USERNAME` — you'll need it in every path below.
> Find it in cPanel top-right corner or run `whoami` in Terminal.

---

## Part 3 — SSH Into the Server and Clone the Repo

### 3.1 Enable SSH on GoDaddy

```
cPanel → SSH Access → Manage SSH Keys → Generate New Key → Authorize it
```

Then connect from your local machine:

```bash
ssh YOUR_USERNAME@YOUR_DOMAIN_OR_IP
```

(GoDaddy also has a Terminal inside cPanel — you can use that instead.)

### 3.2 Remove the empty folder cPanel created

cPanel created an empty `/home/YOUR_USERNAME/dstair/` folder.
Delete it so git can clone into that path:

```bash
rm -rf ~/dstair
```

### 3.3 Clone your GitHub repo

```bash
cd ~
git clone https://github.com/YOUR_GITHUB_USERNAME/YOUR_REPO_NAME.git dstair
```

This clones the repo into `/home/YOUR_USERNAME/dstair/`.

After cloning, verify the structure looks right:

```bash
ls ~/dstair
# Should show: app.py  passenger_wsgi.py  config.py  requirements.txt
# instance/  routes/  models/  templates/  static/  ...
```

Also confirm the database arrived:

```bash
ls ~/dstair/instance/
# Should show: database.db
```

---

## Part 4 — Install Dependencies

### 4.1 Activate the virtualenv cPanel created

```bash
source ~/virtualenv/dstair/3.11/bin/activate
```

Your prompt should now start with `(dstair)`.

### 4.2 Install all packages

```bash
cd ~/dstair
pip install -r requirements.txt
```

This will take 1–2 minutes. Wait for it to fully finish.

### 4.3 Verify the key packages installed

```bash
pip show flask flask-sqlalchemy reportlab
# Each should show a Version line
```

---

## Part 5 — Create the .env File on the Server

### 5.1 Generate a secure SECRET_KEY

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output — it will look like:
`a3f9b2c1e4d5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f3a4b5c6d7e8f9a0b1`

### 5.2 Get your Groq API key

Sign up at [console.groq.com](https://console.groq.com) → API Keys → Create new key.

### 5.3 Create the .env file

```bash
nano ~/dstair/.env
```

Paste this — replacing the placeholder values with real ones:

```
SECRET_KEY=PASTE_YOUR_GENERATED_KEY_HERE
FLASK_ENV=production
DATABASE_URI=sqlite:////home/YOUR_USERNAME/dstair/instance/database.db
GROQ_API_KEY=PASTE_YOUR_GROQ_KEY_HERE
```

> **Critical:** `DATABASE_URI` uses **4 slashes** (`sqlite:////`).
> The first two are the SQLite scheme, the third and fourth begin the absolute path.
> Replace `YOUR_USERNAME` with your actual cPanel username.

Save: `Ctrl+X` → `Y` → `Enter`

### 5.4 Lock down the .env file permissions

```bash
chmod 600 ~/dstair/.env
```

---

## Part 6 — Set Folder Permissions

The web process needs write access to the `instance/` folder (for SQLite writes):

```bash
chmod 755 ~/dstair/instance
chmod 644 ~/dstair/instance/database.db
```

Also allow the static/uploads directory if it exists:

```bash
mkdir -p ~/dstair/static/uploads
chmod 755 ~/dstair/static/uploads
```

---

## Part 7 — Point cPanel to the Cloned Repo

When you cloned into `dstair/`, it replaced the folder cPanel originally created —
so cPanel already points to the right place.

Go back to **cPanel → Setup Python App** → click on your `dstair` app.

Confirm these fields still show correctly:

| Field | Expected value |
| --- | --- |
| Application root | `dstair` |
| Application startup file | `passenger_wsgi.py` |
| Application Entry point | `application` |

If anything changed, fix it here and hit **Save**.

---

## Part 8 — Restart and Test

### 8.1 Restart the app

In **cPanel → Setup Python App** → click your app → click **Restart**.

Or via SSH:

```bash
touch ~/dstair/passenger_wsgi.py
```

(Touching the startup file triggers Passenger to restart.)

### 8.2 Visit your site

Open your domain in a browser. The app should load.

### 8.3 If you see a 500 error

Check the error log:

```bash
# cPanel error log (check the last 30 lines)
tail -30 ~/logs/YOUR_DOMAIN.error.log

# Or in cPanel → Logs → Error Log
```

Common causes and fixes:

| Error message | Fix |
| --- | --- |
| `FATAL: SECRET_KEY contains insecure default` | Check `.env` — `SECRET_KEY` must be set |
| `ModuleNotFoundError` | Re-run `pip install -r requirements.txt` with virtualenv active |
| `sqlite3.OperationalError: unable to open database` | Check `DATABASE_URI` path in `.env` — must use 4 slashes and correct username |
| `Permission denied` on `instance/` | Run `chmod 755 ~/dstair/instance` |
| `No module named 'app'` | Confirm `passenger_wsgi.py` exists and `Application root` in cPanel = `dstair` |

---

## Part 9 — Point Your Domain (If Not Already)

If you bought the domain on GoDaddy and the hosting is on the same account,
the domain is already pointed to your hosting — no DNS changes needed.

If the domain is on a **different** GoDaddy account or registrar:

1. Find your hosting server IP:
   - cPanel → **Server Information** → look for **Shared IP Address**
2. In the domain's DNS settings, add:
   - `A record` → `@` → `YOUR_HOSTING_IP`
   - `A record` → `www` → `YOUR_HOSTING_IP`
   - TTL: `600`
3. DNS propagation takes up to 24 hours.

---

## Part 10 — Updating the App After Changes

Whenever you push new code to GitHub, update the server:

```bash
ssh YOUR_USERNAME@YOUR_DOMAIN_OR_IP

# Pull latest code
cd ~/dstair
git pull origin main

# If requirements.txt changed, reinstall:
source ~/virtualenv/dstair/3.11/bin/activate
pip install -r requirements.txt

# Restart the app
touch ~/dstair/passenger_wsgi.py
```

### Updating the database

If you want the latest local database state on the server:

1. Commit the updated `instance/database.db` locally:

   ```bash
   git add instance/database.db
   git commit -m "chore: update database snapshot"
   git push origin main
   ```

2. On the server:

   ```bash
   cd ~/dstair
   git pull origin main
   touch passenger_wsgi.py
   ```

> If the server database has data you want to keep (user activity, analyses),
> do NOT overwrite it with a git pull. Instead, skip `git pull` on the db file
> or use `git checkout HEAD -- instance/database.db` only when you explicitly
> want to reset the server data back to your local snapshot.

---

## Quick Reference Cheat Sheet

```bash
# ── First deploy (run once) ──────────────────────────────────────
ssh YOUR_USERNAME@YOUR_DOMAIN
rm -rf ~/dstair
git clone https://github.com/YOU/REPO.git dstair
source ~/virtualenv/dstair/3.11/bin/activate
cd ~/dstair && pip install -r requirements.txt
nano ~/dstair/.env                          # fill in SECRET_KEY, DATABASE_URI, GROQ_API_KEY
chmod 600 ~/dstair/.env
chmod 755 ~/dstair/instance
chmod 644 ~/dstair/instance/database.db
touch ~/dstair/passenger_wsgi.py            # restart

# ── Every subsequent update ──────────────────────────────────────
cd ~/dstair && git pull origin main
touch passenger_wsgi.py
```

---

## File Reference

| File | Purpose |
| --- | --- |
| `passenger_wsgi.py` | Phusion Passenger entry point — cPanel looks for this exact name |
| `instance/database.db` | SQLite database — tracked in git so seeded data ships with the code |
| `.env` | Secret keys — created manually on the server, never committed |
| `requirements.txt` | Python dependencies — installed into cPanel's virtualenv |
| `config.py` | Reads `.env` vars; uses `ProductionConfig` when `FLASK_ENV=production` |
