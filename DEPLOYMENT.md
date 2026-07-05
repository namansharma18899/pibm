# Deploying PIBM on AWS (Simple Guide)

This guide uses a single EC2 instance — the simplest way to get your app live.

---

## Part 1: Launch an EC2 Instance

### Step 1 — Create an AWS Account
1. Go to https://aws.amazon.com and click "Create an AWS Account"
2. You get 12 months of free tier (includes 1 free `t2.micro` or `t3.micro` instance)

### Step 2 — Launch an Instance
1. Go to **EC2 Dashboard** → **Launch Instance**
2. Settings:
   - **Name:** `pibm-server`
   - **AMI:** Ubuntu Server 24.04 LTS (free tier eligible)
   - **Instance type:** `t2.micro` (free tier) or `t3.micro`
   - **Key pair:** Click "Create new key pair" → name it `pibm-key` → download the `.pem` file
   - **Network settings:** Check all three boxes:
     - Allow SSH traffic (port 22)
     - Allow HTTPS traffic (port 443)
     - Allow HTTP traffic (port 80)
   - **Storage:** 8 GB (default, free tier eligible)
3. Click **Launch Instance**

### Step 3 — Get Your Public IP
1. Go to **EC2 → Instances** → click your instance
2. Copy the **Public IPv4 address** (e.g. `3.91.45.123`)

### Step 4 — Allocate an Elastic IP (so the IP doesn't change on reboot)
1. Go to **EC2 → Elastic IPs** → **Allocate Elastic IP address** → **Allocate**
2. Select the new IP → **Actions → Associate Elastic IP address**
3. Choose your `pibm-server` instance → **Associate**
4. Note: Elastic IP is free as long as it's attached to a running instance

---

## Part 2: Set Up the Server

### Step 5 — SSH into Your Server

```bash
# Make the key file secure (required)
chmod 400 ~/Downloads/pibm-key.pem

# Connect
ssh -i ~/Downloads/pibm-key.pem ubuntu@YOUR_ELASTIC_IP
```

### Step 6 — Install Dependencies

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3 python3-pip python3-venv nginx certbot python3-certbot-nginx git
```

### Step 7 — Upload Your Code

**Option A — Git (if your code is on GitHub):**
```bash
cd /home/ubuntu
git clone https://github.com/YOUR_USERNAME/pibm.git
cd pibm
```

**Option B — SCP (copy directly from your Mac):**
```bash
# Run this on YOUR MAC, not the server
scp -i ~/Downloads/pibm-key.pem -r /Users/namsharm/personal/projects/pibm ubuntu@YOUR_ELASTIC_IP:/home/ubuntu/pibm
```

### Step 8 — Set Up the App on the Server

```bash
cd /home/ubuntu/pibm

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
nano .env
```

Edit `.env` with your Google OAuth credentials. **Important:** Update the redirect URI in Google Cloud Console to `https://yourdomain.com/auth/google` (you'll set the domain later).

---

## Part 3: Run the App with Systemd (keeps it running forever)

### Step 9 — Create a Systemd Service

```bash
sudo nano /etc/systemd/system/pibm.service
```

Paste this:

```ini
[Unit]
Description=PIBM FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/pibm
Environment="PATH=/home/ubuntu/pibm/.venv/bin"
ExecStart=/home/ubuntu/pibm/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable pibm
sudo systemctl start pibm

# Check it's running
sudo systemctl status pibm
```

---

## Part 4: Set Up Nginx (reverse proxy, port 80 → 8000)

### Step 10 — Configure Nginx

```bash
sudo nano /etc/nginx/sites-available/pibm
```

Paste this:

```nginx
server {
    listen 80;
    server_name YOUR_DOMAIN_OR_IP;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable it:

```bash
sudo ln -s /etc/nginx/sites-available/pibm /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx
```

Your app is now live at `http://YOUR_ELASTIC_IP`.

---

## Part 5: Free Custom Domain

You have a few options for getting a free domain name:

### Option A — DuckDNS (Recommended, simplest)

1. Go to https://www.duckdns.org
2. Sign in with Google/GitHub
3. Pick a subdomain — you'll get something like `pibm.duckdns.org`
4. Enter your EC2 Elastic IP and click **Update**
5. Done — `pibm.duckdns.org` now points to your server

### Option B — FreeDNS (afraid.org)

1. Go to https://freedns.afraid.org
2. Create an account
3. Go to **Subdomains → Add a subdomain**
4. Pick from thousands of shared domains (e.g. `pibm.mooo.com`)
5. Set the **Destination** to your Elastic IP
6. Done

### Option C — No-IP

1. Go to https://www.noip.com
2. Create a free account
3. Create a hostname like `pibm.ddns.net`
4. Point it to your Elastic IP
5. Note: Free tier requires you to confirm the hostname every 30 days

After choosing one, update the `server_name` in your Nginx config:

```bash
sudo nano /etc/nginx/sites-available/pibm
# Change: server_name YOUR_DOMAIN_OR_IP;
# To:     server_name pibm.duckdns.org;

sudo nginx -t
sudo systemctl restart nginx
```

---

## Part 6: Free HTTPS with Let's Encrypt

Once your domain is pointing to your server:

```bash
sudo certbot --nginx -d pibm.duckdns.org
```

- Enter your email
- Agree to terms
- Choose to redirect HTTP to HTTPS (option 2)

Certbot auto-renews. Your site is now on `https://pibm.duckdns.org`.

---

## Part 7: Update Google OAuth

1. Go to https://console.cloud.google.com → **APIs & Services → Credentials**
2. Edit your OAuth 2.0 Client ID
3. Under **Authorized redirect URIs**, add:
   ```
   https://pibm.duckdns.org/auth/google
   ```
4. Update your `.env` on the server if the client ID/secret changed
5. Restart the app:
   ```bash
   sudo systemctl restart pibm
   ```

---

## Useful Commands

```bash
# Check app status
sudo systemctl status pibm

# View app logs
sudo journalctl -u pibm -f

# Restart after code changes
cd /home/ubuntu/pibm && git pull
sudo systemctl restart pibm

# Restart nginx after config changes
sudo nginx -t && sudo systemctl restart nginx
```

---

## Cost Summary

| Item | Cost |
|---|---|
| EC2 t2.micro | Free for 12 months, then ~$8.50/month |
| Elastic IP | Free (while attached to running instance) |
| Domain (DuckDNS) | Free forever |
| HTTPS (Let's Encrypt) | Free forever |
| Storage (8 GB) | Free for 12 months |

**Total: $0 for the first year.**
