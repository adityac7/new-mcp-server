# 🚀 MCP Analytics Server - Permanent Deployment Guide

## Quick Deployment to Render.com (Free Tier)

Follow these steps to deploy your MCP Analytics Server permanently on Render.com's free tier.

---

## Step 1: Create a GitHub Repository

### Option A: Using GitHub Web Interface (Recommended)

1. Go to [github.com](https://github.com) and log in
2. Click the "+" icon → "New repository"
3. Repository name: `mcp-analytics-server`
4. Description: "MCP Analytics Server for Digital Insights"
5. Make it **Public** (required for Render free tier)
6. **DO NOT** initialize with README (we already have files)
7. Click "Create repository"

### Option B: Using GitHub CLI

```bash
# Login to GitHub
gh auth login

# Create repository
cd /home/ubuntu/mcp_analytics_deploy
gh repo create mcp-analytics-server --public --source=. --remote=origin --push
```

### Manual Push (If using Option A)

After creating the repository on GitHub:

```bash
cd /home/ubuntu/mcp_analytics_deploy
git remote add origin https://github.com/YOUR_USERNAME/mcp-analytics-server.git
git push -u origin main
```

---

## Step 2: Create Render Account

1. Go to [render.com](https://render.com)
2. Click "Get Started for Free"
3. Sign up with GitHub (recommended) or email
4. Verify your email address

---

## Step 3: Create PostgreSQL Database on Render

1. In Render Dashboard, click "**New +**" → "**PostgreSQL**"
2. Fill in the details:
   - **Name**: `analytics-db`
   - **Database**: `analytics_db` (leave default)
   - **User**: `analytics_user` (leave default)
   - **Region**: Choose closest to you (e.g., Oregon, Frankfurt, Singapore)
   - **PostgreSQL Version**: 16 (latest)
   - **Plan**: **Free** (1GB storage, 90 days retention)
3. Click "**Create Database**"
4. Wait for database to be created (~2 minutes)
5. Once ready, go to the database page and copy the "**External Database URL**"
   - It looks like: `postgres://analytics_user:password@dpg-xxxxx.oregon-postgres.render.com/analytics_db`
   - **Save this URL** - you'll need it in the next steps

---

## Step 4: Load Data to Cloud Database

On your local machine or sandbox:

```bash
# Set the database URL (use the URL from Step 3)
export DATABASE_URL="postgres://analytics_user:password@dpg-xxxxx.oregon-postgres.render.com/analytics_db"

# Navigate to the deployment directory
cd /home/ubuntu/mcp_analytics_deploy

# Run the data loading script
python3 load_data_cloud.py
```

This will:
- Connect to your local PostgreSQL
- Connect to Render PostgreSQL
- Create the table structure
- Migrate all 839,077 rows
- Create indexes for performance
- Takes ~5-10 minutes

**Expected output**:
```
Connecting to local database...
Connecting to cloud database...
Creating table in cloud database...
Table created successfully
Fetching data from local database...
Inserting data into cloud database...
Inserted 10000 rows...
Inserted 20000 rows...
...
Inserted 839077 rows...
Creating indexes...
Indexes created successfully
Data migration complete! Total rows in cloud database: 839077
```

---

## Step 5: Deploy Web Service on Render

1. In Render Dashboard, click "**New +**" → "**Web Service**"
2. Click "**Connect a repository**"
3. If first time, click "**Configure account**" to connect GitHub
4. Select your repository: `mcp-analytics-server`
5. Click "**Connect**"
6. Fill in the deployment settings:

   **Basic Settings**:
   - **Name**: `mcp-analytics-server` (or your preferred name)
   - **Region**: Same as your database (important!)
   - **Branch**: `main`
   - **Root Directory**: (leave blank)
   - **Runtime**: **Python 3**
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn server:app --host 0.0.0.0 --port $PORT`

   **Advanced Settings**:
   - **Plan**: **Free** (750 hours/month, 512 MB RAM)
   - **Environment Variables**: Click "**Add Environment Variable**"
     - **Key**: `DATABASE_URL`
     - **Value**: Paste the External Database URL from Step 3
       - **Important**: Change `postgres://` to `postgresql://` in the URL
       - Example: `postgresql://analytics_user:password@dpg-xxxxx.oregon-postgres.render.com/analytics_db`

7. Click "**Create Web Service**"

---

## Step 6: Wait for Deployment

Render will now:
1. Clone your repository
2. Install dependencies (takes ~2-3 minutes)
3. Start the server
4. Assign a permanent URL

**Watch the logs** to see progress. You should see:
```
==> Installing dependencies...
==> Successfully installed fastapi uvicorn psycopg2-binary...
==> Starting service...
INFO:     Started server process
INFO:     Uvicorn running on http://0.0.0.0:10000
INFO:     Application startup complete.
```

Once you see "**Live**" status with a green checkmark, your server is deployed!

---

## Step 7: Get Your Permanent URL

Your server will be available at:
```
https://mcp-analytics-server-XXXX.onrender.com
```

(The exact URL will be shown in the Render dashboard)

**Test it**:
```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{"status": "healthy", "database": "connected"}
```

---

## Step 8: Configure ChatGPT Desktop

1. Open **ChatGPT Desktop** application
2. Go to **Settings** → **Beta Features** → **MCP Servers**
3. Add this configuration:

```json
{
  "mcpServers": {
    "analytics": {
      "url": "https://your-app.onrender.com",
      "transport": "http",
      "description": "Digital Insights Analytics - 839K rows"
    }
  }
}
```

4. **Restart ChatGPT Desktop**
5. Test by asking: "Show me the schema of the digital_insights database"

---

## 🎉 You're Done!

Your MCP Analytics Server is now permanently deployed and accessible at:

**URL**: `https://your-app.onrender.com`

### Available Endpoints

- `GET /` - Server info
- `GET /health` - Health check
- `GET /api/schema` - Get table schema
- `GET /api/sample?limit=10` - Get sample data
- `POST /api/query` - Execute custom SQL query
- `GET /api/stats` - Get database statistics
- `POST /api/value_counts` - Get frequency distributions
- `GET /docs` - Interactive API documentation (Swagger UI)

---

## 📊 Test Your Deployment

### 1. Health Check
```bash
curl https://your-app.onrender.com/health
```

### 2. Get Statistics
```bash
curl https://your-app.onrender.com/api/stats
```

### 3. Get Schema
```bash
curl https://your-app.onrender.com/api/schema
```

### 4. Get Sample Data
```bash
curl https://your-app.onrender.com/api/sample?limit=5
```

### 5. Execute Query
```bash
curl -X POST https://your-app.onrender.com/api/query \
  -H "Content-Type: application/json" \
  -d '{"query": "SELECT type, COUNT(*) as count FROM digital_insights GROUP BY type"}'
```

### 6. Interactive Documentation
Open in browser: `https://your-app.onrender.com/docs`

---

## ⚠️ Important Notes

### Free Tier Limitations

**PostgreSQL Free Tier**:
- 1 GB storage (your data uses ~150 MB, plenty of room)
- 90 days data retention (data expires after 90 days)
- Shared CPU and 256 MB RAM

**Web Service Free Tier**:
- 750 hours/month (enough for 24/7 operation)
- Spins down after **15 minutes of inactivity**
- **Cold start**: Takes ~30 seconds to wake up on first request
- 512 MB RAM

### Cold Starts

On the free tier, your server will "sleep" after 15 minutes of no requests. The first request after sleep will take ~30 seconds to respond. Subsequent requests will be fast.

**To avoid cold starts**: Upgrade to Starter plan ($7/month) for always-on service.

### Data Retention

Free PostgreSQL databases expire after 90 days. To keep your data permanently:
- Upgrade to Starter plan ($7/month) for unlimited retention
- Or export and re-import data every 90 days

---

## 🔒 Security Considerations

### Current Setup (Testing)
- ✅ No authentication (open access)
- ✅ Query whitelisting (only SELECT)
- ✅ Row limits (max 1000 rows)
- ✅ Keyword blocking (no DROP, DELETE, etc.)

### For Production
Consider adding:
- OAuth 2.0 authentication
- API key authentication
- Rate limiting
- IP whitelisting
- HTTPS only (already enabled by Render)

---

## 📈 Monitoring & Maintenance

### View Logs
1. Go to Render Dashboard
2. Click on your web service
3. Click "Logs" tab
4. View real-time logs

### Monitor Performance
1. Check "Metrics" tab in Render
2. View CPU, memory, and response times
3. Set up alerts (available on paid plans)

### Update Code
```bash
cd /home/ubuntu/mcp_analytics_deploy
# Make changes to server.py or other files
git add .
git commit -m "Update: description of changes"
git push origin main
```

Render will automatically detect the push and redeploy (takes ~2-3 minutes).

---

## 🆙 Upgrading from Free Tier

When you're ready for production:

### Database Upgrade ($7/month)
- 10 GB storage
- Unlimited retention
- Dedicated resources
- Daily backups

### Web Service Upgrade ($7/month)
- Always-on (no cold starts)
- 1 GB RAM
- Dedicated resources
- Better performance

**Total**: $14/month for production-ready setup

---

## 🐛 Troubleshooting

### Issue: Database connection failed

**Check**:
1. DATABASE_URL is set correctly in Render environment variables
2. URL format is `postgresql://` not `postgres://`
3. Database is running (check Render dashboard)

**Fix**:
```bash
# Test connection manually
psql "postgresql://user:pass@host/db"
```

### Issue: Server not responding

**Check**:
1. Server status in Render dashboard (should be "Live")
2. Logs for errors
3. If on free tier, wait 30 seconds for cold start

**Fix**:
- Restart service from Render dashboard
- Check logs for specific error messages

### Issue: Data not loaded

**Check**:
1. Run data loading script again
2. Verify DATABASE_URL is accessible
3. Check local database has data

**Fix**:
```bash
# Verify cloud database
psql "$DATABASE_URL" -c "SELECT COUNT(*) FROM digital_insights;"
```

### Issue: ChatGPT can't connect

**Check**:
1. URL is correct in ChatGPT config
2. Server is running (check /health endpoint)
3. ChatGPT Desktop is restarted

**Fix**:
- Test URL in browser: `https://your-app.onrender.com/`
- Check Render logs for connection attempts

---

## 📞 Support

### Render Support
- Documentation: [render.com/docs](https://render.com/docs)
- Community: [community.render.com](https://community.render.com)
- Status: [status.render.com](https://status.render.com)

### MCP Server Issues
- Check logs in Render dashboard
- Test endpoints with curl
- Review server.py code
- Check database connection

---

## 🎯 Next Steps

1. ✅ Deploy to Render (you're doing this now!)
2. ✅ Test all endpoints
3. ✅ Configure ChatGPT Desktop
4. ⬜ Add more datasets (incrementally)
5. ⬜ Implement authentication (optional)
6. ⬜ Set up monitoring (optional)
7. ⬜ Upgrade to paid tier (when ready)

---

## 📝 Deployment Checklist

- [ ] GitHub repository created
- [ ] Code pushed to GitHub
- [ ] Render account created
- [ ] PostgreSQL database created on Render
- [ ] Database URL copied
- [ ] Data loaded to cloud database (839K rows)
- [ ] Web service created on Render
- [ ] DATABASE_URL environment variable set
- [ ] Deployment successful (status: Live)
- [ ] Health check passes
- [ ] All endpoints tested
- [ ] ChatGPT Desktop configured
- [ ] Connection tested with ChatGPT

---

**Congratulations!** 🎉

Your MCP Analytics Server is now permanently deployed and accessible worldwide!

**Permanent URL**: `https://your-app.onrender.com`  
**Status**: Live 24/7 (with cold starts on free tier)  
**Data**: 839K rows of digital insights  
**Cost**: $0/month (free tier)

