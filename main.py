"""Compatibility entry point for deployments that import main:app.

The canonical FastAPI application lives in backend.api.main.
"""

from backend.api.main import app

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from backend.agent.agent import create_agent
from backend.agent.chat_tool_router import (
    build_chat_response_payload,
    build_tool_context,
    route_chat_tools,
)
from backend.core.pipeline import run_grocery_pipeline
from backend.core.gpt56_client import generate_primary_or_fallback
from auth import get_current_user
from backend.db.recipe_cache_repository import list_recipes, user_save_recipe
from backend.db.rate_limit_repository import (
    check_generate_limit,
    check_gemini_limit,
    check_chat_limit,
    increment_usage,
)
import base64
from backend.db.store_prices_repository import save_store_prices

# ── Config ────────────────────────────────────────────────────────────────────
MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://smartcart-mcp-505176174078.us-central1.run.app/mcp"
)

session_service = InMemorySessionService()
APP_NAME = "smartcart"
runner = None


# ── MCP helper (proper MCP protocol) ─────────────────────────────────────────
async def call_mcp_tool(tool_name: str, arguments: dict) -> dict:
    async with httpx.AsyncClient(timeout=30) as client:
        req_id = int(time.time() * 1000)

        # Step 1: Initialize
        init_res = await client.post(MCP_SERVER_URL,
            headers=[("Content-Type", "application/json"), ("Accept", "application/json, text/event-stream")],
            json={"jsonrpc": "2.0", "id": req_id, "method": "initialize",
                  "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                             "clientInfo": {"name": "smartcart-agent", "version": "1.0"}}}
        )
        session_id = init_res.headers.get("mcp-session-id")
        if not session_id:
            raise ValueError(f"No session id. Headers: {dict(init_res.headers)}")

        # Step 2: Notify initialized
        await client.post(MCP_SERVER_URL,
            headers=[("Content-Type", "application/json"), ("Accept", "application/json, text/event-stream"), ("mcp-session-id", session_id)],
            json={"jsonrpc": "2.0", "method": "notifications/initialized"}
        )

        # Step 3: Call tool
        tool_res = await client.post(MCP_SERVER_URL,
            headers=[("Content-Type", "application/json"), ("Accept", "application/json, text/event-stream"), ("mcp-session-id", session_id)],
            json={"jsonrpc": "2.0", "id": req_id + 1, "method": "tools/call",
                  "params": {"name": tool_name, "arguments": arguments}}
        )
        print(f"[MCP] {tool_name} → {tool_res.status_code}: {tool_res.text[:500]}")
        print(f"[MCP] raw tool response: '{tool_res.text}'")

        for line in tool_res.text.splitlines():
            line = line.strip()
            if line.startswith("data: "):
                raw = line[6:].strip()
                if not raw or raw == "[DONE]":
                    continue
                data = json.loads(raw)
                if "error" in data:
                    raise ValueError(f"MCP tool error: {data['error']}")
                result = data.get("result", {})
                content = result.get("content", [])
                if content:
                    text = content[0].get("text", "")
                    if not text or not text.strip():
                        return {}
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError:
                        return {"text": text}
        return {}

# ── Lifespan (ADK runner init) ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    global runner
    agent = create_agent()
    runner = Runner(
        agent=agent,
        app_name=APP_NAME,
        session_service=session_service,
    )
    yield


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Grocery AI",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ────────────────────────────────────────────────────────────────────
class DishRequest(BaseModel):
    weekly_meals:           dict           = {}
    manual_items:           List[str]      = []
    budget:                 float          = 100
    user_id:                str            = "demo_user"
    pantry_items:           List[str]      = []
    dietary_instruction:    str            = "Vegetarian only"
    mode:                   str            = "🍽️ Meal Only"
    selected_substitutions: Dict[str, str] = {}
    user_lat: float | None = None
    user_lng: float | None = None
    force_refresh: bool = False

class ChatRequest(BaseModel):
    session_id: str = "default"
    message:    str

class ReceiptUploadRequest(BaseModel):
    image_base64: str        # base64-encoded image or PDF
    media_type:   str        # "image/jpeg" | "image/png" | "application/pdf"
    store_name:   str  = ""
    address:      str  = ""
    city:         str  = ""
    state:        str  = ""
    country:      str  = "US"
    receipt_date: str  = ""
    lat: float | None = None
    lng: float | None = None
    
# ── Add this Pydantic model near your other request models (e.g. after ReceiptUploadRequest) ──

class FeedbackRequest(BaseModel):
    email:   str = ""
    comment: str


# ── Add this route near your other routes (e.g. after /receipt/stores) ──

@app.post("/feedback")
async def submit_feedback(body: FeedbackRequest, user: dict = Depends(get_current_user)):
    """
    Sends user feedback (improvement ideas, beta-testing issues) via email
    to the SmartCart team. Not stored in Firestore — email only.
    """
    from backend.services.email_service import send_feedback_email

    try:
        result = send_feedback_email(
            user_email=body.email,
            comment=body.comment,
            user_id=user["uid"],
        )
        if not result["success"]:
            return {"success": False, "error": result.get("error", "Failed to send feedback.")}
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}    


# ── Routes ────────────────────────────────────────────────────────────────────
@app.get("/")
def home():
    return {"message": "Smart Grocery AI API is running 🚀"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/generate")
def generate(request: DishRequest, user: dict = Depends(get_current_user)):
    try:
        if not request.weekly_meals and not request.manual_items:
            raise HTTPException(
                status_code=400,
                detail="Provide weekly_meals, manual_items, or both."
            )
        uid = user["uid"]
        print(f"[generate] weekly_meals received: {request.weekly_meals}")

        # ── Rate limit: Places API (every /generate) ──────────────────
        gen_check = check_generate_limit(uid)
        if not gen_check["allowed"]:
            raise HTTPException(status_code=429, detail=gen_check["message"])

        # ── Rate limit: Gemini (cache miss only) ──────────────────────
        gemini_check = check_gemini_limit(uid)
        # Pass gemini_allowed into pipeline so unified_ai_agent can skip
        # Gemini and return cache-only result if limit is hit

        result = run_grocery_pipeline(
            user_id=uid,
            weekly_meals=request.weekly_meals,
            manual_items=request.manual_items,
            budget=request.budget,
            pantry_items=request.pantry_items,
            dietary_instruction=request.dietary_instruction,
            mode=request.mode,
            selected_substitutions=request.selected_substitutions,
            user_lat=request.user_lat,
            user_lng=request.user_lng,
            force_refresh=request.force_refresh,
            gemini_allowed=gemini_check["allowed"],
        )

        # ── Increment counters based on what was actually called ──────
        increment_usage(uid, "generate")  # always — Places API was called
        if result.get("_gemini_called"):  # only if Gemini was actually used
            increment_usage(uid, "gemini")

        # Attach usage info to response for frontend display
        result["_usage"] = {
            "generate": {"used": gen_check["used"] + 1, "limit": gen_check["limit"]},
            "gemini": {"used": gemini_check["used"] + (1 if result.get("_gemini_called") else 0),
                       "limit": gemini_check["limit"]},
        }

        return result

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]

    # ── Rate limit: chat ──────────────────────────────────────────────
    chat_check = check_chat_limit(uid)
    if not chat_check["allowed"]:
        return {
            "response": f"⚠ {chat_check['message']}",
            "session_id": req.session_id,
            "steps": [],
            "cards": {"shopping_list": [], "stores": [], "recipes": []},
            "usage": {"used": chat_check["used"], "limit": chat_check["limit"]},
            "rate_limited": True,
        }

    tool_results = route_chat_tools(req.message, uid)
    tool_context = build_tool_context(tool_results)

    prompt = f"""You are SmartCart, an AI grocery and meal planning assistant.

Backend tool results, if any:
{tool_context}

User question: {req.message}

Answer directly and concisely. Ground your answer in the backend tool results when tools were used.
If no backend tools matched this message, answer normally without claiming you checked pantry, recipes, stores, or prices."""

    # GPT-5.6 is primary here; retain Gemini as the resilience fallback.
    def generate_with_gemini(chat_prompt: str) -> str:
        from vertexai.generative_models import GenerativeModel
        model = GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))
        return model.generate_content(chat_prompt).text

    response_text, _model_used = generate_primary_or_fallback(
        prompt,
        generate_with_gemini,
        log_prefix="chat",
    )

    increment_usage(uid, "chat")

    return build_chat_response_payload(
        response_text=response_text,
        session_id=req.session_id,
        tool_results=tool_results,
        usage={"used": chat_check["used"] + 1, "limit": chat_check["limit"]},
    )


# /debug/pantry/{user_id} removed — it let anyone query any user's pantry by
# guessing a uid, with no auth check. Replaced with an auth-protected version
# that only returns the caller's own pantry.
@app.get("/debug/pantry/me")
async def debug_pantry_me(user: dict = Depends(get_current_user)):
    try:
        result = await call_mcp_tool("get_pantry_items", {"user_id": user["uid"]})
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


@app.put("/pantry")
async def update_pantry(body: dict, user: dict = Depends(get_current_user)):
    uid = user["uid"]  # verified, not from URL
    try:
        items = body.get("items", [])
        print(f"[pantry] updating {uid}: {items}")
        result = await call_mcp_tool("update_pantry_items", {
            "user_id": uid,
            "items": items
        })
        print(f"[update_pantry] result: {result}")
        return {"result": result, "success": True}
    except Exception as e:
        print(f"[update_pantry] failed: {e}")
        return {"error": str(e), "success": False}


@app.get("/debug/tools")
async def debug_tools():
    try:
        from google.adk.tools.mcp_tool import MCPToolset, StreamableHTTPConnectionParams
        toolset = MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=MCP_SERVER_URL,
                timeout=60,
            )
        )
        tools = await toolset.get_tools()
        return {"tools": [t.name for t in tools], "count": len(tools)}
    except Exception as e:
        return {"error": str(e)}


class RecipeSaveRequest(BaseModel):
    meal: str
    ingredients: list
    instructions: list = []

@app.get("/recipes/me")
async def get_recipes(user: dict = Depends(get_current_user)):
    """List all saved recipes for the authenticated user."""
    try:
        recipes = list_recipes(user["uid"])
        return {"recipes": recipes, "count": len(recipes), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}

@app.put("/recipes")
async def save_recipe(body: RecipeSaveRequest, user: dict = Depends(get_current_user)):
    """Save or update a recipe from the Recipe page."""
    try:
        result = user_save_recipe(
            user_id=user["uid"],
            meal=body.meal,
            ingredients=body.ingredients,
            instructions=body.instructions,
        )
        return {"result": result, "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}


@app.post("/receipt/upload")
async def upload_receipt(body: ReceiptUploadRequest, user: dict = Depends(get_current_user)):
    """
    Upload a grocery receipt photo or PDF.
    Gemini Vision extracts store name, items and prices.
    Saved to store_prices collection for real price lookups.
    """
    import base64
    from backend.db.store_prices_repository import save_store_prices
    from vertexai.generative_models import GenerativeModel, Part as VPart

    uid = user["uid"]

    try:
        # ── Decode base64 ─────────────────────────────────────────────
        try:
            image_bytes = base64.b64decode(body.image_base64)
        except Exception:
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

        # ── Build Gemini Vision prompt ────────────────────────────────
        prompt = """You are a grocery receipt parser.
Extract ALL items and their prices from this receipt.
Also extract the store name if visible.

Return ONLY valid JSON in this exact format:
{
  "store_name": "<store name from receipt or empty string>",
  "receipt_date": "<date from receipt in YYYY-MM-DD format or empty string>",
  "items": {
    "<item name lowercase>": {"price": <float>, "unit": "<unit or empty>"},
    "<item name lowercase>": {"price": <float>, "unit": "<unit or empty>"}
  }
}

RULES:
- item names must be lowercase
- price must be a number (no $ sign)
- unit examples: "lb", "oz", "each", "bag", "can", "bottle", ""
- if you cannot read a price clearly, skip that item
- No markdown, no explanation, valid JSON only"""

        # ── Call Gemini Vision ────────────────────────────────────────
        import vertexai
        vertexai.init(project=os.getenv("GOOGLE_PROJECT_ID"), location="us-central1")
        model = GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))

        media_type = body.media_type
        if media_type == "application/pdf":
            # Gemini handles PDF as document
            part = VPart.from_data(data=image_bytes, mime_type="application/pdf")
        else:
            part = VPart.from_data(data=image_bytes, mime_type=media_type)

        response = model.generate_content([part, prompt])
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        parsed = json.loads(text)

        # ── Resolve store details ─────────────────────────────────────
        # User-provided values override Gemini-extracted values
        store_name = body.store_name.strip() or parsed.get("store_name", "").strip() or "Unknown Store"
        city = body.city.strip()
        state = body.state.strip()
        country = body.country.strip() or "US"
        address = body.address.strip()
        receipt_date = body.receipt_date.strip() or parsed.get("receipt_date", "")
        items = parsed.get("items", {})

        if not items:
            return {"success": False, "error": "No items found in receipt. Please try a clearer photo."}

        if not city or not state:
            return {
                "success": False,
                "error": "Could not determine store location. Please enter city and state.",
                "store_name": store_name,
                "items": items,
            }

        # ── Save to Firestore ─────────────────────────────────────────
        result = save_store_prices(
            uploaded_by=uid,
            store_name=store_name,
            city=city,
            state=state,
            country=country,
            address=address,
            items=items,
            receipt_date=receipt_date,
            lat=body.lat,
            lng=body.lng,
        )

        return {
            "success": True,
            "store_name": store_name,
            "city": city,
            "state": state,
            "item_count": result["item_count"],
            "items_preview": dict(list(items.items())[:5]),  # first 5 for UI preview
            "store_id": result["store_id"],
        }

    except HTTPException:
        raise
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"Could not parse receipt. Try a clearer photo. ({e})"}
    except Exception as e:
        traceback.print_exc()
        return {"success": False, "error": str(e)}


@app.get("/receipt/stores")
async def get_nearby_stores_with_prices(
        city: str, state: str,
        user: dict = Depends(get_current_user)
):
    """List stores with uploaded price data for a city."""
    from backend.db.store_prices_repository import get_stores_in_city
    try:
        stores = get_stores_in_city(city, state)
        return {"stores": stores, "count": len(stores), "success": True}
    except Exception as e:
        return {"error": str(e), "success": False}
