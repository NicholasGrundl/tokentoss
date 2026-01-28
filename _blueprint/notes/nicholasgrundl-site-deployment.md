# Complete Deployment Guide: 0 to 100

*Step-by-step instructions for deploying Astro portfolio site to Digital Ocean*

---

## Prerequisites

Before starting:
- [ ] Digital Ocean account with payment method
- [ ] Domain name registered (nicholasgrundl.com)
- [ ] Local machine with Node.js 18+, npm, Docker
- [ ] Tailscale account (free)
- [ ] Astro project built locally (`npm run build` works)
- [ ] Create `.env` file from `.env.example` with your droplet IP addresses

> **Note on Docker Build**: This guide uses legacy `docker build` commands. You may see a deprecation warning about buildx - this can be safely ignored. The production VM has buildx installed, and we can migrate anytime without breaking changes. See [Appendix: Migrating to Docker Buildx](#appendix-migrating-to-docker-buildx) for migration instructions.

---

## TLDR: Abridged Steps

0. Setup local environment
- copy `.env.example` to `.env` (you'll fill in IPs later)

1. Create Droplet
- obtain public IP address

2. Configure droplet OS
- install tailscale -> obtain tailscale IP address
- **update `.env` file with both IP addresses**
- install caddy
- docker, docker-compose


3. Deploy files to droplet
- transfer docker image
- transfer caddyfile
- transfer docker-compose

4. Launch website
- reload caddy
- start docker-compose

5. Configure DNS
- connect to droplet IP address



## Part 1: Infrastructure Setup (Completed)

### ✅ Step 1: Create Digital Ocean Project

- Project name: `personal-website`
- All resources will be organized under this project

### ✅ Step 2: Configure Firewalls

We create **two reusable firewalls** for different server types:

> **Why two firewalls?**
> - Separation of concerns: public vs internal servers
> - Reusable patterns for future infrastructure
> - Easier to manage security rules per service type

#### Firewall 1: `http-https` (For Public Web Servers)

**Use case**: Servers that need to serve HTTP/HTTPS traffic (web servers, APIs, reverse proxies)

**Inbound rules**:
- SSH (22) - All IPs (will be locked to Tailscale later in Security Hardening)
- HTTP (80) - All IPs
- HTTPS (443) - All IPs
- Tailscale UDP (41641) - All IPs


#### Firewall 2: `no-inbound` (For Backend/Internal Servers)

**Use case**: Servers that should NOT be publicly accessible (databases, Redis, internal APIs, background workers)

**Inbound rules**:
- SSH (22) - Tailscale subnet only (100.0.0.0/8)
- Tailscale UDP (41641) - All IPs


### ✅ Step 3: Launch Ubuntu Droplet

- Hostname: `web01`
- OS: Ubuntu 24.04 LTS
- Firewall: `http-https` attached
- Monitoring: Enabled
- Public IP: [DROPLET_PUBLIC_IP]

### ✅ Step 4: Install and Configure Tailscale

**On droplet:**
```bash
ssh root@DROPLET_PUBLIC_IP
curl -fsSL https://tailscale.com/install.sh | sh
sudo tailscale up
tailscale ip -4
# Note the Tailscale IP: 100.x.x.x -> DROPLET_TAILSCALE_IP
```

> **On local machine:**
> - Installed Tailscale desktop app
> - Authenticated with same account
> - Can SSH via Tailscale IP: `ssh root@DROPLET_TAILSCALE_IP`

### Step 4.1: Create .env File (On Local Machine)

Now that you have both IP addresses, create your local `.env` file for deployment automation:

```bash
# On local machine, in project directory
# Copy the example file
cp .env.example .env

# Edit .env and add your IP addresses
# DROPLET_PUBLIC_IP=206.xxx.xx.xxx      # Replace with your droplet's public IP
# DROPLET_TAILSCALE_IP=100.xx.xxx.x     # Replace with your droplet's Tailscale IP
```

**Verify your .env file contains:**
```bash
cat .env
# Should show:
# DROPLET_PUBLIC_IP=your_actual_public_ip
# DROPLET_TAILSCALE_IP=your_actual_droplet_tailscale_ip
```

**Note**: The `.env` file is git-ignored and will never be committed. This keeps your infrastructure details secure.

### ✅ Step 5: Install Caddy


```bash
ssh root@DROPLET_TAILSCALE_IP

sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | \
  sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | \
  sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# Verify
sudo systemctl status caddy
```

**Note**: Caddy is now installed but not yet configured. The `Caddyfile` lives in your project repository and will be copied to the droplet during deployment (Step 9).

---

## Part 2: Docker Setup

### Step 6: Install Docker and Docker Compose

```bash
ssh root@DROPLET_TAILSCALE_IP

# Update package index
sudo apt update

# Install prerequisites
sudo apt install -y ca-certificates curl gnupg

# Add Docker's GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add Docker repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker
sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Verify installation
docker --version
docker compose version

# Test Docker
docker run hello-world
```

**Expected output:**
```
Docker version 24.x.x
Docker Compose version v2.x.x
Hello from Docker! [success message]
```

### Step 7: Create Application Directory

```bash
ssh root@DROPLET_TAILSCALE_IP

#on droplet
mkdir -p /opt/personal-website
cd /opt/personal-website
```

---

## Part 3: Application Deployment

### Step 8: Build and Deploy

> **These files should already exist in your repository/local machine:**
> `Dockerfile`
> `docker-compose.yaml`
> `.dockerignore`
> `Caddyfile`
> `astro.config.mjs` and `src/` code for building astro site

We manually deploy to the droplet from our local machine

```bash
# On local machine, in project directory

# Build Docker image (this also runs 'npm run build' inside the container) (just docker-build)
docker build -t personal-website:latest .

# Transfer image to droplet (via Tailscale) (just deploy-transfer)
docker save personal-website:latest | gzip | ssh root@DROPLET_TAILSCALE_IP "gunzip | docker load"

# Transfer configuration files (just deploy-config)
scp docker-compose.yml root@DROPLET_TAILSCALE_IP:/opt/personal-website/
scp Caddyfile root@DROPLET_TAILSCALE_IP:/etc/caddy/Caddyfile

# Reload Caddy with new configuration (part of just deploy-caddy)
ssh root@DROPLET_TAILSCALE_IP "sudo systemctl reload caddy"

# Start container on droplet (just deploy-restart)
ssh root@DROPLET_TAILSCALE_IP "cd /opt/personal-website && docker compose up -d"

# Check status (just deploy-status)
ssh root@DROPLET_TAILSCALE_IP "docker compose -f /opt/personal-website/docker-compose.yml ps"

# View logs (just logs-follow)
ssh root@DROPLET_TAILSCALE_IP "docker compose -f /opt/personal-website/docker-compose.yml logs -f"
```

**Expected output:**
```
NAME              IMAGE                      STATUS         PORTS
web               personal-website:latest   Up 10 seconds  127.0.0.1:4321->4321/tcp
```

### Step 9: Test Locally on Droplet

```bash
ssh root@DROPLET_TAILSCALE_IP

# Test Node.js server responds
curl -I http://localhost:4321

# Expected: HTTP/1.1 200 OK

# Test Caddy proxy
curl -I -H "Host: nicholasgrundl.com" http://localhost

# Expected: HTTP/1.1 308 Permanent Redirect to https://nicholasgrundl.com/
# This is good! Caddy is correctly redirecting HTTP to HTTPS and to the canonical domain.
```

---

## Part 4: DNS Configuration

### Step 10: Configure DNS for Caddy & Cloudflare

This is a critical step to get Caddy's automatic HTTPS working correctly with Cloudflare's proxy. We will point the DNS to the droplet, let Caddy get a certificate, and then enable the Cloudflare proxy.

**Assumptions:**
- Your domain `nicholasgrundl.com` is registered with or managed by Cloudflare.
- You are in the "DNS" settings for your domain in the Cloudflare dashboard.

#### Part A: Initial DNS Setup (DNS Only)

First, we create the records but leave them in "DNS only" mode. This allows Caddy to get a certificate from Let's Encrypt.

1.  **Clean up old records:** Delete any existing `A`, `AAAA`, or `CNAME` records for `nicholasgrundl.com` and `www` that might be left over from a previous host.

2.  **Create an `A` record for the root domain:**
    *   **Type**: `A`
    *   **Name**: `@`
    *   **IPv4 address**: Your droplet's public IP (`[DROPLET_PUBLIC_IP]`)
    *   **Proxy status**: **DNS only** (grey cloud)
    *   **TTL**: Auto

3.  **Create a `CNAME` record for `www`:**
    *   **Type**: `CNAME`
    *   **Name**: `www`
    *   **Target**: `nicholasgrundl.com`
    *   **Proxy status**: **DNS only** (grey cloud)
    *   **TTL**: Auto

At this point, your DNS is pointing directly to your server.

#### Part B: Verify Caddy Certificate Acquisition

1.  **Ensure Caddy is running:** The deployment steps in Part 3 should have already started Caddy. If not, SSH into your droplet and run `sudo systemctl reload caddy`.
2.  **Wait for propagation:** Wait 1-2 minutes for the DNS changes to be visible globally.
3.  **Check Caddy logs:** Watch the Caddy logs for the certificate acquisition message.
    ```bash
    ssh root@DROPLET_TAILSCALE_IP "sudo journalctl -u caddy -f"
    # Or using just: just logs-follow
    # Look for messages like "certificate obtained successfully"
    ```
4.  **Verify HTTPS:** From your local machine, test that the site is secure.
    ```bash
    curl -I https://nicholasgrundl.com
    # You should see "HTTP/2 200"
    ```
    You can also open the site in a browser and check for the lock icon.

#### Part C: Enable Cloudflare Proxy (Orange Cloud)

Once you've confirmed your site is working over HTTPS directly, you can enable Cloudflare's proxy to get the performance and security benefits.

1.  **Change Proxy Status:** Go back to your Cloudflare DNS settings. Edit the `A` and `CNAME` records and change their **Proxy status** to **Proxied (orange cloud)**.

2.  **Set SSL/TLS Mode:** In the Cloudflare dashboard, go to the **SSL/TLS** tab for your domain. Set the encryption mode to **Full (Strict)**. This is the most secure option and is required for end-to-end encryption with your Caddy server.

Your site is now fully configured and running through Cloudflare.

### Step 11: Verify Final DNS Configuration

After enabling the Cloudflare proxy, you can verify that DNS is now pointing to Cloudflare's servers, which is the correct final state.

```bash
# Check DNS from local machine
dig nicholasgrundl.com
```

**Expected output (after propagation):**
The `ANSWER SECTION` should now show one or more `A` records pointing to **Cloudflare's IP addresses**, not your droplet's IP. This confirms that traffic is being proxied.

```
;; ANSWER SECTION:
nicholasgrundl.com.    300    IN    A    104.21.x.x
nicholasgrundl.com.    300    IN    A    172.67.x.x
```

You can also check the `www` subdomain:
```bash
dig www.nicholasgrundl.com
# This should show a CNAME record pointing to nicholasgrundl.com,
# and then the same Cloudflare IP addresses.
```

**Check propagation**: You can use a tool like https://dnschecker.org to see your DNS records from multiple locations around the world.

### Step 12: Verify HTTPS Works

**After DNS propagates:**

```bash
# From local machine
curl -I https://nicholasgrundl.com

# Expected: HTTP/2 200

# Check certificate
curl -vI https://nicholasgrundl.com 2>&1 | grep -i issuer
# Expected: Let's Encrypt
```

**In browser:**
- Navigate to: https://nicholasgrundl.com
- Check for padlock icon (secure connection)
- Open DevTools → Console (should be no errors)
- Verify CSS/JS/images all loaded

**Monitor Caddy during first HTTPS request:**
```bash
ssh root@DROPLET_TAILSCALE_IP
sudo journalctl -u caddy -f
# Or using just: just logs-follow

# Watch for:
# "certificate obtained successfully"
```

---

## Part 5: Ongoing Maintenance

This section covers routine tasks to keep your deployment healthy and secure.

### Periodic System Updates

It's good practice to periodically update the packages on your droplet to receive security patches and bug fixes.

```bash
# SSH into your droplet and run:
ssh root@{{DROPLET_TAILSCALE_IP}} "sudo apt update && sudo apt upgrade -y && docker system prune -f"
```

### Manual SSL Certificate Renewal (Every ~60-80 Days)

> **Note:** This manual process is required because the Cloudflare proxy interferes with Caddy's default renewal process. For a permanent, automated solution, see "Automate SSL Certificate Renewal" in the "Future Improvements" section.

Let's Encrypt certificates are valid for 90 days. You should renew them before they expire.

1.  **Disable Cloudflare Proxy:**
    *   In your Cloudflare DNS settings, change the `A` record for `@` and the `CNAME` record for `www` to **DNS only (grey cloud)**.

2.  **Trigger Renewal on Droplet:**
    *   Wait 1-2 minutes for the DNS change to propagate.
    *   SSH into your droplet and restart Caddy. This will trigger it to check its certificates and renew if necessary.
        ```bash
        ssh root@{{DROPLET_TAILSCALE_IP}} "sudo systemctl restart caddy"
        ```

3.  **Verify Renewal:**
    *   Watch the Caddy logs for a success message.
        ```bash
        # Using just:
        just deploy-caddy-logs
        # Or manually:
        ssh root@{{DROPLET_TAILSCALE_IP}} "sudo journalctl -u caddy -f"
        ```

4.  **Re-enable Cloudflare Proxy:**
    *   Once renewal is confirmed, go back to your Cloudflare DNS settings.
    *   Change the `A` and `CNAME` records back to **Proxied (orange cloud)**.

### Monitoring the System

#### DNS, Proxy, and Caddy Health
- **Check DNS Resolution**: Verify that your domain points to Cloudflare's IPs.
  ```bash
  dig nicholasgrundl.com
  ```
- **Check Public Accessibility**: Ensure the site is returning a `200 OK` status through Cloudflare.
  ```bash
  curl -I https://nicholasgrundl.com
  ```
- **Check Caddy Service Status**: Make sure the Caddy service is active and running on the droplet.
  ```bash
  ssh root@{{DROPLET_TAILSCALE_IP}} "sudo systemctl status caddy"
  ```

#### Application & Docker Health
- **Check Container Status**: Verify that your application's Docker container is running.
  ```bash
  # Using just:
  just deploy-status
  # Or manually:
  ssh root@{{DROPLET_TAILSCALE_IP}} "docker compose -f /opt/personal-website/docker-compose.yml ps"
  ```
- **Check Application Logs**: View the logs from your application container for any errors.
  ```bash
  # Using just:
  just deploy-logs-follow
  # Or manually:
  ssh root@{{DROPLET_TAILSCALE_IP}} "docker compose -f /opt/personal-website/docker-compose.yml logs -f"
  ```

#### Traffic and Analytics
- **Caddy Request Logs**: Caddy logs all requests by default. You can view them via `journalctl` to see incoming traffic to your origin server.
  ```bash
  ssh root@{{DROPLET_TAILSCALE_IP}} "sudo journalctl -u caddy"
  ```
- **Cloudflare Analytics**: The Cloudflare dashboard provides a powerful, free analytics suite. Go to the **Analytics & Logs** tab for your domain to see detailed information about traffic, requests, cached content, security events, and performance. This is the best place to get an overview of your site's traffic.

---

## Part 6: Future Improvements

This section contains optional but highly recommended enhancements to make your deployment more robust, secure, and easier to manage.

### Automate SSL Certificate Renewal
As described in the maintenance section, the default Caddy setup requires manual intervention to renew SSL certificates. You can eliminate this by using a free Cloudflare Origin Certificate, which is valid for 15 years.

**Workflow Summary:**
1.  **Generate Certificate in Cloudflare:** Go to **SSL/TLS** -> **Origin Server** in your Cloudflare dashboard and create a 15-year certificate.
2.  **Copy Certificate to Droplet:** Save the certificate and private key, and copy them to `/etc/caddy/certs/` on your droplet.
3.  **Update `Caddyfile`:** Modify your `Caddyfile` to use these files with the `tls` directive:
    ```caddy
    tls /etc/caddy/certs/nicholasgrundl.com.pem /etc/caddy/certs/nicholasgrundl.com.key
    ```
4.  **Deploy and Reload:** Deploy the new `Caddyfile` and reload Caddy.

> For full step-by-step instructions, see the `design/cloudflare-origin-cert.md` file.

### Security Hardening

#### Step A: Lock SSH to Tailscale Only

**⚠️ CRITICAL**: Verify Tailscale access works before this step!

```bash
# Test Tailscale SSH
ssh root@{{DROPLET_TAILSCALE_IP}}
```

**Update Digital Ocean Firewall:**

1. Digital Ocean dashboard → **Networking** → **Firewalls**
2. Edit firewall: `http-https`
3. **Inbound Rules** → SSH (port 22):
   - Remove "All IPv4" and "All IPv6".
   - Add a new source: `100.0.0.0/8` (Tailscale's IP range).
4. Save firewall and test that public IP SSH access is blocked while Tailscale access works.

#### Step B: Configure UFW Firewall

```bash
ssh root@{{DROPLET_TAILSCALE_IP}}
sudo ufw allow from 100.0.0.0/8 to any port 22 proto tcp
sudo ufw allow 41641/udp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw enable
```

#### Step C: Install fail2ban
```bash
ssh root@{{DROPLET_TAILSCALE_IP}} "sudo apt install -y fail2ban && sudo systemctl enable --now fail2ban"
```

#### Step D: Enable Automatic Security Updates
```bash
ssh root@{{DROPLET_TAILSCALE_IP}} "sudo apt install -y unattended-upgrades && sudo dpkg-reconfigure -plow unattended-upgrades"
```

### Deployment Automation

This project uses [Just](https://github.com/casey/just) for deployment automation. The `justfile` in the project root contains all the necessary commands.

**View all available commands:**
```bash
just --list
```

**Deploy to production:**
```bash
just deploy
```

### Automated Backups & Log Rotation

#### Step A: Set Up Backup Script (On Droplet)
A sample backup script and cron job are detailed in the appendix. This should be reviewed and implemented to ensure regular backups of your configuration and data.

#### Step B: Configure Log Rotation
To prevent logs from consuming excessive disk space, configure Docker's log rotation.

**Add to `/etc/docker/daemon.json` on the droplet:**
```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```
Then restart Docker: `sudo systemctl restart docker`.

---

## Troubleshooting

**Site not loading?**
- Check DNS: `dig nicholasgrundl.com`
- Check container: `just deploy-status`
- Check Caddy: `ssh root@{{DROPLET_TAILSCALE_IP}} "sudo systemctl status caddy"`

**SSL not working?**
- Check Caddy logs: `just deploy-caddy-logs`
- Verify DNS propagation: https://dnschecker.org

**Can't SSH?**
- Use Digital Ocean web console (dashboard → droplet → Access → Launch Console)
- Check Tailscale: `tailscale status`

---

## Appendix: Migrating to Docker Buildx

(This section remains unchanged)

