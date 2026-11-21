# Deploying DocRename AI (Free HTTPS Portfolio Stack)

## Recommended Architecture
- **Frontend (Next.js):** **Vercel** (Free Hobby tier, automatic HTTPS)
- **Backend (FastAPI + RapidOCR):** **Hugging Face Spaces (Docker)** — Free tier gives **2 vCPU / 16 GB RAM**, which runs `PyMuPDF` + `RapidOCR (ONNX)` comfortably without OOM errors. *(Alternative: Railway or Render Starter.)*

---

## Step 1: Push to GitHub

```powershell
Set-Location "c:\Users\Pisonet\Desktop\Projects\doc-rename-ai"
git init
git add .
git commit -m "Initial commit: DocRename AI (Next.js + FastAPI hybrid OCR)"
git branch -M main
git remote add origin https://github.com/<your-username>/doc-rename-ai.git
git push -u origin main
```

---

## Step 2: Deploy Backend to Hugging Face Spaces (Free 16GB RAM)

1. Go to https://huggingface.co/new-space
2. Choose:
   - **Space name:** `doc-rename-ai-api`
   - **SDK:** **Docker** → **Blank**
   - **Hardware:** Free CPU basic (2 vCPU, 16 GB RAM)
   - **Visibility:** Public
3. Push the `backend/` folder to your Space repo (or upload `Dockerfile`, `pyproject.toml`, `uv.lock`, `app/`, and `eval/`):
   ```powershell
   git clone https://huggingface.co/spaces/<hf-username>/doc-rename-ai-api ../hf-space
   Copy-Item -Recurse -Force backend\Dockerfile, backend\pyproject.toml, backend\uv.lock, backend\app, backend\eval ..\hf-space\
   Set-Location ..\hf-space
   git add .
   git commit -m "Deploy DocRename AI FastAPI backend"
   git push
   ```
4. *(Optional)* In Space **Settings → Variables and secrets**, add:
   - `LLM_PROVIDER=gemini` (or `openai`)
   - `GEMINI_API_KEY=...` (as a **Secret**)
5. Verify your backend is live at:
   `https://<hf-username>-doc-rename-ai-api.hf.space/api/health`

---

## Step 3: Deploy Frontend to Vercel (Free HTTPS)

1. Go to https://vercel.com/new and import your `doc-rename-ai` GitHub repository.
2. Set **Root Directory** to `frontend`.
3. Add **Environment Variable**:
   - `BACKEND_URL` = `https://<hf-username>-doc-rename-ai-api.hf.space`
4. Click **Deploy**.

Next.js automatically proxies `/api/*` to `BACKEND_URL`, so your mobile phone gets a clean HTTPS URL (`https://doc-rename-ai.vercel.app`) with camera scanning (`capture="environment"`) and zero CORS issues.
