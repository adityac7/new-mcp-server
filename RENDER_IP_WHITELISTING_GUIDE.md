# Render IP Whitelisting Guide for Database Connections

## The Problem

Your external databases require IP whitelisting, but Render's outbound IP addresses can change during deployments.

## How Render IPs Work

### ❌ Free Tier (Current Plan)
- **Outbound IPs**: Shared pool, can change anytime
- **No static IPs**: IPs rotate during deployments
- **Unpredictable**: Cannot whitelist reliably

### ✅ Paid Plans (Starter $7/month+)
- **Static outbound IPs**: Available on paid plans
- **Stable**: IPs don't change during deployments
- **Whitelistable**: Can be added to database firewall rules

## Solution Options

### Option 1: Upgrade to Render Starter Plan (Recommended)

**Cost**: $7/month per service

**Benefits**:
- ✅ Static outbound IP addresses
- ✅ IPs remain stable across deployments
- ✅ One-time whitelist setup
- ✅ Better performance and reliability

**How to get static IPs**:
1. Upgrade to Starter plan or higher
2. Contact Render support to enable static IPs
3. They'll provide you with 2-3 static IPs for your region (Singapore)
4. Whitelist these IPs in your database firewall

**Steps**:
```bash
# 1. Upgrade service to Starter plan
Go to: https://dashboard.render.com/web/srv-d3s5o9pr0fns73a858ug
Settings → Plan → Upgrade to Starter

# 2. Request static IPs
Email: support@render.com
Subject: Request Static Outbound IPs for srv-d3s5o9pr0fns73a858ug
Body: "Please enable static outbound IPs for my service in Singapore region"

# 3. They'll respond with IPs like:
# - 52.76.123.45
# - 54.169.234.56
# - 13.228.67.89

# 4. Whitelist these IPs in your database
```

---

### Option 2: Use SSH Tunnel / Bastion Host

**Cost**: Free (if you have a VPS) or $5-10/month for a small VPS

**How it works**:
1. Set up a small VPS with a static IP (e.g., AWS EC2 t2.micro, DigitalOcean Droplet)
2. Whitelist the VPS IP in your database
3. Configure SSH tunnel from Render to VPS to Database

**Implementation**:

```python
# app/database_tunnel.py
import sshtunnel
import os

def create_tunnel():
    """Create SSH tunnel to database through bastion host"""
    tunnel = sshtunnel.SSHTunnelForwarder(
        ('your-bastion-host.com', 22),
        ssh_username='ubuntu',
        ssh_pkey='/app/ssh_key',
        remote_bind_address=('your-database-host.com', 5432),
        local_bind_address=('127.0.0.1', 5432)
    )
    tunnel.start()
    return tunnel

# Then connect to localhost:5432 instead of remote database
```

**Pros**:
- ✅ Works on free tier
- ✅ Full control
- ✅ Can use for multiple databases

**Cons**:
- ❌ More complex setup
- ❌ Additional infrastructure to maintain
- ❌ Potential latency

---

### Option 3: Use Render Private Network (Team Plan)

**Cost**: $19/month per member

**How it works**:
- Render Team plan includes private networking
- Deploy a PostgreSQL proxy service on Render
- Proxy has static IP, connects to your databases
- MCP server connects to proxy via private network

**Not recommended** unless you need Team features anyway.

---

### Option 4: Use Cloud SQL Proxy / Database Proxy

**Cost**: Free (built into cloud providers)

**For Google Cloud SQL**:
```dockerfile
# Add to Dockerfile
RUN wget https://dl.google.com/cloudsql/cloud_sql_proxy.linux.amd64 -O /usr/local/bin/cloud_sql_proxy
RUN chmod +x /usr/local/bin/cloud_sql_proxy

# Start proxy before server
CMD cloud_sql_proxy -instances=PROJECT:REGION:INSTANCE=tcp:5432 & python server.py
```

**For AWS RDS**:
- Use IAM authentication instead of IP whitelisting
- No static IP needed

**Pros**:
- ✅ No IP whitelisting needed
- ✅ Works on free tier
- ✅ More secure (uses IAM/service accounts)

**Cons**:
- ❌ Only works with specific cloud providers
- ❌ Requires cloud provider setup

---

### Option 5: VPN Connection (Advanced)

**Cost**: $5-15/month for VPN service

**How it works**:
1. Set up WireGuard/OpenVPN server with static IP
2. Configure Render service to connect through VPN
3. Whitelist VPN IP in database

**Not recommended** - too complex for this use case.

---

## Recommended Solution: Option 1 (Static IPs)

For your use case, **upgrading to Render Starter plan** is the best solution:

### Why?
1. **Simple**: One-time setup, no ongoing maintenance
2. **Reliable**: IPs don't change, no connection issues
3. **Affordable**: $7/month is reasonable for production
4. **Professional**: Static IPs are standard for production services

### Implementation Steps:

#### Step 1: Upgrade to Starter Plan
```
1. Go to https://dashboard.render.com/web/srv-d3s5o9pr0fns73a858ug
2. Click "Settings" → "Plan"
3. Select "Starter" ($7/month)
4. Confirm upgrade
```

#### Step 2: Request Static IPs
```
Email: support@render.com
Subject: Request Static Outbound IPs

Body:
Hi Render Team,

I've upgraded my service (srv-d3s5o9pr0fns73a858ug) to the Starter plan 
and would like to request static outbound IP addresses for the Singapore region.

Service: new-mcp-server
Region: Singapore
Use case: Connecting to whitelisted external databases

Thank you!
```

#### Step 3: Wait for Response (usually 24-48 hours)
Render support will provide you with 2-3 static IPs like:
```
52.76.123.45
54.169.234.56
13.228.67.89
```

#### Step 4: Whitelist IPs in Your Databases
Add these IPs to your database firewall rules:
- PostgreSQL: Update `pg_hba.conf` or cloud provider firewall
- MySQL: Update firewall rules
- MongoDB: Update network access settings

#### Step 5: Test Connection
```bash
# Test from Render service
curl https://new-mcp-server.onrender.com/health
```

---

## Alternative: If You Must Stay on Free Tier

If you can't upgrade, use **Option 4 (Cloud SQL Proxy)** if your databases are on:
- Google Cloud SQL
- AWS RDS (use IAM auth)
- Azure Database

Otherwise, use **Option 2 (SSH Tunnel)** with a cheap VPS ($5/month DigitalOcean Droplet).

---

## Current Service Info

**Service ID**: `srv-d3s5o9pr0fns73a858ug`
**Region**: Singapore
**Current Plan**: Free
**URL**: https://new-mcp-server.onrender.com

---

## Summary

| Option | Cost | Complexity | Reliability | Recommended |
|--------|------|------------|-------------|-------------|
| 1. Static IPs (Starter) | $7/mo | Low | High | ⭐⭐⭐⭐⭐ |
| 2. SSH Tunnel | $5/mo | Medium | Medium | ⭐⭐⭐ |
| 3. Private Network | $19/mo | Low | High | ⭐⭐ |
| 4. Cloud Proxy | Free | Medium | High | ⭐⭐⭐⭐ |
| 5. VPN | $10/mo | High | Medium | ⭐ |

**Best choice**: Upgrade to Starter plan and request static IPs from Render support.

---

## Questions?

Let me know which option you'd like to implement and I can help you set it up!

