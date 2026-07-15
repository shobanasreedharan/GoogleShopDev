@echo off
echo ==========================================
echo  SmartCart AI - Full Deploy Script
echo ==========================================

REM ---- CONFIG ----
set PROJECT=hackathon-grocery-ai-498023
set REGION=us-central1
set MONGO_URI=mongodb+srv://shobanaram06:Lavanya%%40123@clustergooglecloud.dgzpo1y.mongodb.net/smart_grocery?retryWrites=true^&w=majority
set MONGO_DB=smart_grocery
set GEMINI_MODEL=gemini-2.5-flash
set GCP_LOCATION=us-central1

REM ==========================================
REM  STEP 1: Build and Deploy MCP Server
REM ==========================================
echo.
echo [1/4] Building MCP image...
copy Dockerfile.mcp Dockerfile /Y
gcloud builds submit --tag gcr.io/%PROJECT%/smartcart-mcp --project %PROJECT%
if %ERRORLEVEL% neq 0 (del Dockerfile && echo BUILD FAILED for MCP && exit /b 1)
del Dockerfile

echo.
echo [2/4] Deploying MCP service...
gcloud run deploy smartcart-mcp ^
  --image gcr.io/%PROJECT%/smartcart-mcp ^
  --region %REGION% ^
  --platform managed ^
  --allow-unauthenticated ^
  --set-env-vars "MDB_MCP_CONNECTION_STRING=%MONGO_URI%,MONGO_DB=%MONGO_DB%" ^
  --project %PROJECT%
if %ERRORLEVEL% neq 0 (echo DEPLOY FAILED for MCP && exit /b 1)

REM ==========================================
REM  STEP 2: Build and Deploy API Server
REM ==========================================
echo.
echo [3/4] Building API image...
copy Dockerfile.app Dockerfile /Y
gcloud builds submit --tag gcr.io/%PROJECT%/smartcart-api --project %PROJECT%
if %ERRORLEVEL% neq 0 (del Dockerfile && echo BUILD FAILED for API && exit /b 1)
del Dockerfile

echo.
echo [4/4] Deploying API service...
gcloud run deploy smartcart-api ^
  --image gcr.io/%PROJECT%/smartcart-api ^
  --region %REGION% ^
  --platform managed ^
  --allow-unauthenticated ^
  --set-env-vars "MDB_MCP_CONNECTION_STRING=%MONGO_URI%,MONGO_DB=%MONGO_DB%,GOOGLE_CLOUD_PROJECT=%PROJECT%,GEMINI_MODEL_NAME=%GEMINI_MODEL%,GOOGLE_GENAI_USE_VERTEXAI=true,GOOGLE_CLOUD_LOCATION=%GCP_LOCATION%" ^
  --project %PROJECT%
if %ERRORLEVEL% neq 0 (echo DEPLOY FAILED for API && exit /b 1)

echo.
echo ==========================================
echo  ALL DONE! Both services deployed.
echo ==========================================
echo MCP:  https://smartcart-mcp-505176174078.us-central1.run.app
echo API:  Check Cloud Run console for smartcart-api URL
echo ==========================================
