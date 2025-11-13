# VM Deployment Guide

Deploy the MCP Analytics Server with Web UI on any Linux VM.

## Prerequisites

- Ubuntu 20.04+ or similar Linux distribution
- Python 3.11+
- PostgreSQL connection for metadata storage
- OpenAI API key (for metadata generation)

## Quick Start

### 1. Install System Dependencies

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install Python 3.11
sudo apt-get install -y python3.11 python3.11-venv python3-pip

# Install PostgreSQL client libraries
sudo apt-get install -y libpq-dev gcc g++

# Install Git
sudo apt-get install -y git
```

### 2. Clone Repository

```bash
cd ~
git clone <your-repo-url> mcp-server
cd mcp-server
```

### 3. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
```

### 4. Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env file
nano .env
```

**Required environment variables:**

```env
# Metadata Database (where datasets info is stored)
DATABASE_URL=postgresql://user:password@host:port/metadata_db

# Encryption Key (generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
ENCRYPTION_KEY=<your-fernet-key-here>

# OpenAI API Key (for AI metadata generation)
OPENAI_API_KEY=sk-<your-key-here>

# Optional: Redis (for hot-reload, can leave empty)
REDIS_URL=

# Optional: Query row limit
MAX_ROWS=40
```

### 6. Initialize Database

```bash
# Run database migrations
alembic upgrade head
```

### 7. Start the Server

**Option A: Simple start (foreground)**

```bash
python start_ui.py
```

**Option B: Using uvicorn directly**

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

**Option C: Production with Gunicorn**

```bash
gunicorn app.main:app \
  --bind 0.0.0.0:8000 \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker \
  --timeout 120 \
  --access-logfile - \
  --error-logfile -
```

### 8. Access the UI

Open your browser and navigate to:

```
http://your-vm-ip:8000/ui
```

## Adding Your First Dataset

1. Go to `http://your-vm-ip:8000/ui/datasets`
2. Click "Add Dataset"
3. Fill in the form:
   - **Dataset Name**: e.g., "Analytics Database"
   - **Description**: Brief description (optional)
   - **Connection String**: `postgresql://user:password@host:port/database`
4. Click "Add Dataset"
5. The system will:
   - Test the connection
   - Encrypt and store the connection string
   - Profile the database schema
   - Generate AI metadata (if OpenAI key is configured)

## Production Deployment Tips

### Using systemd Service

Create `/etc/systemd/system/mcp-server.service`:

```ini
[Unit]
Description=MCP Analytics Server
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/home/your-user/mcp-server
Environment="PATH=/home/your-user/mcp-server/venv/bin"
ExecStart=/home/your-user/mcp-server/venv/bin/python start_ui.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable mcp-server
sudo systemctl start mcp-server
sudo systemctl status mcp-server
```

### Using Nginx Reverse Proxy

Install Nginx:

```bash
sudo apt-get install -y nginx
```

Create `/etc/nginx/sites-available/mcp-server`:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable and restart:

```bash
sudo ln -s /etc/nginx/sites-available/mcp-server /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### Firewall Configuration

```bash
# Allow SSH
sudo ufw allow ssh

# Allow HTTP/HTTPS
sudo ufw allow 80
sudo ufw allow 443

# Or allow specific port
sudo ufw allow 8000

# Enable firewall
sudo ufw enable
```

## Query Limits

- **All queries**: Limited to 40 rows
- **Aggregated queries** (with GROUP BY): 40 rows
- **Raw data queries** (no GROUP BY): 40 rows

This limit prevents large data transfers and ensures fast responses.

## Troubleshooting

### Connection Errors

If you can't connect to the database:

1. Check connection string format:
   ```
   postgresql://user:password@host:port/database
   ```

2. Test manually:
   ```bash
   psql "postgresql://user:password@host:port/database"
   ```

3. Check firewall rules on database server

### Encryption Key Errors

If you see "ENCRYPTION_KEY environment variable not set":

```bash
# Generate a new key
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# Add to .env
echo "ENCRYPTION_KEY=<generated-key>" >> .env
```

### UI Not Loading

1. Check if server is running:
   ```bash
   curl http://localhost:8000/health
   ```

2. Check logs:
   ```bash
   journalctl -u mcp-server -f
   ```

3. Verify templates exist:
   ```bash
   ls -la app/ui/templates/
   ```

## Monitoring

Check server logs:

```bash
# If using systemd
sudo journalctl -u mcp-server -f

# If running directly
tail -f logs/server.log
```

## Updating

```bash
cd ~/mcp-server
git pull
source venv/bin/activate
pip install -r requirements.txt --upgrade
alembic upgrade head
sudo systemctl restart mcp-server
```

## Support

For issues or questions, check:
- Server logs
- Database connectivity
- Environment variables

## Security Notes

⚠️ **Important Security Considerations:**

1. **No Authentication**: This server has NO authentication by default
   - Only deploy on trusted networks or behind a VPN
   - Use firewall rules to restrict access
   - Consider adding authentication layer (nginx basic auth, VPN, etc.)

2. **Connection Strings**: Encrypted but stored in database
   - Protect your metadata database
   - Rotate encryption keys periodically

3. **Environment Variables**:
   - Never commit `.env` file to git
   - Use secure methods to store secrets
