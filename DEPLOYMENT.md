# Deploying DocRename AI (100% Free HTTPS Stack)

- **Backend (FastAPI + RapidOCR):** **Render** (Free Web Service via Docker, auto-deploys from GitHub)
- **Frontend (Next.js):** **Vercel** (Free Hobby tier, automatic HTTPS)

---

## Step 1: Deploy Backend to Render (Free)

1. Go to https://dashboard.render.com and sign in with GitHub.
2. Click **New + → Web Service** (or **New + → Blueprint** to auto-import `render.yaml`).
3. Select your `doc-rename-ai` GitHub repository and configure:
   - **Name:** `doc-rename-ai-api`
   - **Root Directory:** `backend`
   - **Language / Runtime:** `Docker`
   - **Instance Type:** `Free`
   - **Health Check Path:** `/api/health`
4. *(Optional)* Add environment variables under **Environment** to enable live LLM fallback:
   - `LLM_PROVIDER` = `gemini` (or `openai`)
   - `GEMINI_API_KEY` = `<your-key>`
5. Click **Create Web Service**.
6. Once the build finishes and status is **Live**, verify:
   `https://<your-render-service>.onrender.com/api/health`

*(Note: Render's Free tier sleeps after 15 minutes of inactivity; the first request after sleep takes ~30–50 seconds to wake up.)*

---

## Step 2: Deploy Frontend to Vercel (Free HTTPS)

1. Go to https://vercel.com/new and import your `doc-rename-ai` GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Add **Environment Variable**:
   - **Name:** `BACKEND_URL`
   - **Value:** `https://<your-render-service>.onrender.com` *(no trailing slash)*
4. Click **Deploy**.

Next.js proxies `/api/*` directly to `BACKEND_URL`, so your mobile phone gets a clean HTTPS URL (`https://<your-app>.vercel.app`) with camera scanning (`capture="environment"`) and zero CORS issues.
