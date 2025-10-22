# MCP Analytics Server - Deployment Guide

## 🎯 Overview

This guide will walk you through deploying the MCP Analytics Server to Render using the Blueprint feature.

## ✅ Pre-Deployment Checklist

- [x] Code pushed to GitHub: `adityac7/new-mcp-server`
- [x] Database migration complete (metadata_text column added)
- [x] Encryption key fixed and tested locally
- [x] All core functions tested and working
- [x] Local server tested with public URL
- [x] render.yaml configuration updated

## 🚀 Deployment Steps

### Step 1: Deploy via Render Blueprint

1. Go to https://render.com/
2. Click "New" → "Blueprint"
3. Connect your GitHub repository: `adityac7/new-mcp-server`
4. Select the `main` branch
5. Render will detect the `render.yaml` file automatically

### Step 2: Configure Environment Variables

After the blueprint is created, you need to set these environment variables **manually** for both services:

#### For `mcp-analytics-server`:

```bash
DATABASE_URL=postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug

ENCRYPTION_KEY=JyfitDWGZt7Phv5jX6vr_DMaCmI56a3mAcRxGjiVjIQ=

OPENAI_API_KEY=<your-openai-api-key>
```

#### For `mcp-analytics-ui`:

```bash
DATABASE_URL=postgresql://analytics_db_clug_user:sa1jEkjEmuIKRxQu3x6Oa83Ep4AWGSAM@dpg-d3pmmtali9vc73bn81i0-a.singapore-postgres.render.com/analytics_db_clug

ENCRYPTION_KEY=JyfitDWGZt7Phv5jX6vr_DMaCmI56a3mAcRxGjiVjIQ=

OPENAI_API_KEY=<your-openai-api-key>
```

**⚠️ CRITICAL:** The `ENCRYPTION_KEY` **MUST** be the same for both services. Otherwise, the UI won't be able to decrypt the connection strings stored by the MCP server.

### Step 3: Wait for Deployment

Render will:
1. Create the Redis instance (`mcp-analytics-redis`)
2. Build and deploy the MCP server (`mcp-analytics-server`)
3. Build and deploy the UI dashboard (`mcp-analytics-ui`)

This typically takes 5-10 minutes.

### Step 4: Verify Deployment

Once deployed, you'll have:

1. **MCP Server URL**: `https://mcp-analytics-server.onrender.com/mcp`
2. **UI Dashboard URL**: `https://mcp-analytics-ui.onrender.com`

Test the MCP server:
```bash
curl https://mcp-analytics-server.onrender.com/mcp
```

You should see an error about "Client must accept text/event-stream" - this is expected and means the server is running.

### Step 5: Generate Metadata (Optional but Recommended)

After deployment, generate AI metadata for your dataset:

1. SSH into the MCP server (or run locally with production DATABASE_URL)
2. Run:
```bash
python3 generate_metadata.py 1
```

This will generate metadata for dataset ID 1 using GPT-4.1-mini.

## 🔗 Connect to ChatGPT

### Option 1: ChatGPT Desktop (Recommended)

1. Open ChatGPT Desktop
2. Go to Settings → Integrations → MCP Servers
3. Add a new server:
   - **Name**: MCP Analytics
   - **URL**: `https://mcp-analytics-server.onrender.com/mcp`
   - **Transport**: HTTP (Server-Sent Events)
4. Save and test the connection

### Option 2: ChatGPT Web (via Custom GPT)

1. Create a Custom GPT
2. Add the MCP server URL as an action
3. Configure the action schema (see CHATGPT_CONNECTION_GUIDE.md)

## 📊 Available MCP Tools

Once connected, ChatGPT will have access to these 6 tools:

1. **list_available_datasets()** - List all datasets
2. **get_dataset_schema(dataset_id)** - Get schema for a dataset
3. **query_dataset(dataset_id, query, apply_weights)** - Execute SQL query
4. **get_dataset_sample(dataset_id, table_name, limit)** - Get sample data
5. **get_context(level, dataset_id)** - Get progressive context (0-3)
6. **execute_multi_query(queries, apply_weights)** - Execute multiple queries in parallel

## 🎨 UI Dashboard Features

Access the UI dashboard at `https://mcp-analytics-ui.onrender.com` to:

- Add new datasets
- View dataset schemas
- Test queries
- View query logs
- Manage metadata

## 🔧 Troubleshooting

### Issue: "InvalidToken" error

**Cause**: ENCRYPTION_KEY mismatch between services

**Solution**: Ensure both services have the **exact same** ENCRYPTION_KEY

### Issue: Server not responding

**Cause**: Render free tier may spin down after 15 minutes of inactivity

**Solution**: First request will take 30-60 seconds to wake up the server

### Issue: Database connection error

**Cause**: DATABASE_URL not set correctly

**Solution**: Double-check the DATABASE_URL in environment variables

## 📈 Performance Notes

- **Free Tier Limitations**:
  - Server spins down after 15 minutes of inactivity
  - 512MB RAM limit
  - 0.1 CPU cores
  - 750 hours/month free

- **Optimization**:
  - Markdown responses save 50% tokens
  - Progressive context loading (4 levels)
  - 5-row raw data limit enforcement
  - Automatic query result caching via Redis

## 🔐 Security Notes

- Connection strings are encrypted with Fernet (AES-128)
- Only SELECT queries allowed
- SQL injection protection via sqlparse
- Rate limiting via Redis
- Environment variables stored securely on Render

## 📝 Next Steps

1. Test all 6 MCP tools via ChatGPT
2. Generate metadata for dataset ID 1
3. Monitor query logs in the UI dashboard
4. Add more datasets as needed
5. Consider upgrading to paid tier for production use

## 🆘 Support

For issues or questions:
- Check the logs in Render dashboard
- Review PRECISE_ANALYSIS.md for technical details
- Check CODE_REVIEW.md for implementation details

