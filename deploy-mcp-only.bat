@echo off
echo ==========================================
echo  SmartCart AI - Deploy MCP Only
echo ==========================================

REM ---- CONFIG ----
set PROJECT=hackathon-grocery-ai-498023
set REGION=us-central1
set MONGO_URI=mongodb+srv://shobanaram06:Lavanya%%40123@clustergooglecloud.dgzpo1y.mongodb.net/smart_grocery?retryWrites=true^&w=majority
set MONGO_DB=smart_grocery

echo.
echo [1/2] Building MCP image...
copy Dockerfile.mcp Dockerfile /Y
gcloud builds submit --tag gcr.io/%PROJECT%/smartcart-mcp --project %PROJECT%
if %ERRORLEVEL% neq 0 (del Dockerfile && echo BUILD FAILED && exit /b 1)
del Dockerfile

echo.
echo [2/2] Deploying MCP service...
gcloud run deploy smartcart-mcp --image gcr.io/hackathon-grocery-ai-498023/smartcart-mcp --region us-central1 --platform managed --allow-unauthenticated --set-env-vars "MDB_MCP_CONNECTION_STRING=mongodb+srv://shobanaram06:Lavanya%40123@clustergooglecloud.dgzpo1y.mongodb.net/smart_grocery?retryWrites=true&w=majority,MONGO_DB=smart_grocery,FORWARDED_ALLOW_IPS=*" --project hackathon-grocery-ai-498023
if %ERRORLEVEL% neq 0 (echo DEPLOY FAILED && exit /b 1)

echo.
echo ==========================================
echo  DONE! MCP deployed.
echo ==========================================
echo Test MCP:
echo   curl -X POST https://smartcart-mcp-505176174078.us-central1.run.app/mcp -H "Content-Type: application/json" -d "{\"tool\":\"mongo\",\"action\":\"get_pantry\",\"payload\":{\"user_id\":\"demo_user\"}}"
echo ==========================================
