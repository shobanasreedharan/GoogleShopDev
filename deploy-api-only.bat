@echo off
echo ==========================================
echo  SmartCart AI - Deploy API Only
echo ==========================================

REM ---- CONFIG ----
set PROJECT=hackathon-grocery-ai-498023
set REGION=us-central1
set GEMINI_MODEL=gemini-2.5-flash
set GCP_LOCATION=us-central1

echo.
echo [1/2] Building API image...
copy Dockerfile.api Dockerfile /Y
gcloud builds submit --tag gcr.io/%PROJECT%/smartcart-api --project %PROJECT%
if %ERRORLEVEL% neq 0 (del Dockerfile && echo BUILD FAILED && exit /b 1)
del Dockerfile

echo.
echo [2/2] Deploying API service...
gcloud run deploy smartcart-api ^
  --image gcr.io/%PROJECT%/smartcart-api ^
  --region %REGION% ^
  --platform managed ^
  --allow-unauthenticated ^
  --project %PROJECT%
if %ERRORLEVEL% neq 0 (echo DEPLOY FAILED && exit /b 1)

echo.
echo ==========================================
echo  DONE! API deployed.
echo ==========================================
echo Test health:
echo   curl https://smartcart-api-505176174078.us-central1.run.app/health
echo Test pantry:
echo   curl https://smartcart-api-505176174078.us-central1.run.app/debug/pantry/demo_user
echo ==========================================
