# MCP Analytics Server - Cloud Deployment

## Deployment to Render.com

This is the cloud-ready version of the MCP Analytics Server, optimized for deployment on Render.com's free tier.

## Features

- ✅ FastAPI-based HTTP API
- ✅ PostgreSQL database support
- ✅ 839K rows of digital insights data
- ✅ 5 analytical endpoints
- ✅ Security controls (query whitelisting, row limits)
- ✅ CORS enabled for cross-origin access
- ✅ Auto-scaling and health checks

## Deployment Steps

### 1. Create Render Account

Go to [render.com](https://render.com) and sign up for a free account.

### 2. Create PostgreSQL Database

1. Click "New +" → "PostgreSQL"
2. Name: `analytics-db`
3. Database: `analytics_db`
4. User: `analytics_user`
5. Region: Choose closest to you
6. Plan: **Free** (1GB storage, 90 days retention)
7. Click "Create Database"
8. Copy the **External Database URL** (starts with `postgres://`)

### 3. Load Data to Database

On your local machine:

```bash
# Set the database URL
export DATABASE_URL="postgres://analytics_user:password@host/analytics_db"

# Run the data loading script
python3 load_data_cloud.py
```

This will migrate all 839K rows from your local database to the cloud.

### 4. Deploy Web Service

1. Click "New +" → "Web Service"
2. Connect your GitHub repository (or use "Deploy from Git URL")
3. Name: `mcp-analytics-server`
4. Region: Same as database
5. Branch: `main`
6. Runtime: **Python 3**
7. Build Command: `pip install -r requirements.txt`
8. Start Command: `uvicorn server:app --host 0.0.0.0 --port $PORT`
9. Plan: **Free** (750 hours/month)
10. Environment Variables:
    - `DATABASE_URL`: Paste the External Database URL from step 2
11. Click "Create Web Service"

### 5. Wait for Deployment

Render will:
- Install dependencies
- Start the server
- Assign a permanent URL (e.g., `https://mcp-analytics-server.onrender.com`)

## Alternative: Deploy via GitHub

### 1. Push to GitHub

```bash
cd /home/ubuntu/mcp_analytics_deploy
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/mcp-analytics-server.git
git push -u origin main
```

### 2. Connect Render to GitHub

1. In Render dashboard, click "New +" → "Web Service"
2. Click "Connect GitHub"
3. Select your repository
4. Follow steps 3-11 from above

## API Endpoints

Once deployed, your server will have these endpoints:

- `GET /` - Server info
- `GET /health` - Health check
- `GET /api/schema` - Get table schema
- `GET /api/sample?limit=10` - Get sample data
- `POST /api/query` - Execute custom SQL query
- `GET /api/stats` - Get database statistics
- `POST /api/value_counts` - Get frequency distributions

## Usage Examples

### Get Schema

```bash
curl https://your-app.onrender.com/api/schema
```

### Get Sample Data

```bash
curl https://your-app.onrender.com/api/sample?limit=10
```

### Execute Query

```bash
curl -X POST https://your-app.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT type, COUNT(*) FROM digital_insights GROUP BY type"}'
```

### Get Statistics

```bash
curl https://your-app.onrender.com/api/stats
```

## Configuration for MCP Clients

### For ChatGPT Desktop (OpenAI)

1. Open ChatGPT Settings → Connectors → Advanced → Developer Mode
2. Enable Developer Mode
3. Add your deployed MCP server using the Streamable HTTP endpoint:

**Configuration:**
```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app.onrender.com/mcp"
    }
  }
}
```

**Note:** ChatGPT cannot connect to localhost. You must deploy to a public URL (e.g., Render, ngrok, etc.)

### For Claude Desktop

1. Open Claude Desktop Settings → Developer → Edit Config
2. Add the following to `claude_desktop_config.json`:

**For Remote Server (Deployed):**
```json
{
  "mcpServers": {
    "analytics": {
      "transport": {
        "type": "http",
        "url": "https://your-app.onrender.com/mcp"
      }
    }
  }
}
```

**For Local Development:**
```json
{
  "mcpServers": {
    "analytics": {
      "transport": {
        "type": "http",
        "url": "http://localhost:8000/mcp"
      }
    }
  }
}
```

**Note:** The `/mcp` endpoint is critical - don't forget it!

### For Claude Code (VS Code Extension)

Use the CLI command:
```bash
claude mcp add --transport http analytics https://your-app.onrender.com/mcp
```

Or for local:
```bash
claude mcp add --transport http analytics http://localhost:8000/mcp
```

## Free Tier Limits

### Render PostgreSQL Free Tier
- 1 GB storage
- 90 days data retention
- Shared CPU
- 256 MB RAM

### Render Web Service Free Tier
- 750 hours/month
- Shared CPU
- 512 MB RAM
- Spins down after 15 min inactivity
- Cold start: ~30 seconds

## Security

- Only SELECT queries allowed
- Maximum 1000 rows per query
- Dangerous keywords blocked
- SQL injection protection
- Environment-based configuration

## Monitoring

- Health endpoint: `/health`
- Render provides automatic health checks
- View logs in Render dashboard
- Automatic restart on failure

## Scaling

To upgrade from free tier:

1. **Database**: Upgrade to Starter ($7/month) for 10GB storage
2. **Web Service**: Upgrade to Starter ($7/month) for always-on service

## Troubleshooting

### Database Connection Failed

Check that:
1. DATABASE_URL is set correctly
2. Database is running (check Render dashboard)
3. Database URL format is `postgresql://` not `postgres://`

### Server Not Responding

1. Check Render logs for errors
2. Verify the server is running (check Render dashboard)
3. On free tier, wait 30 seconds for cold start

### Data Not Loading

1. Verify local database has data
2. Check DATABASE_URL is accessible
3. Review data loading script logs

## Support

For issues:
1. Check Render status page
2. Review server logs in Render dashboard
3. Test endpoints with curl
4. Check database connection

## Next Steps

1. Deploy to Render
2. Test all endpoints
3. Configure ChatGPT Desktop
4. Add authentication (optional)
5. Set up monitoring (optional)

