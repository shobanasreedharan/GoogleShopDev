from dotenv import load_dotenv
load_dotenv()

import os
import json
import httpx
import time
import traceback
from contextlib import asynccontextmanager
from typing import List, Dict

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from backend.agent.agent import create_agent
from backend.agent.chat_tool_router import (
    build_chat_response_payload,
    build_tool_context,
    route_chat_tools,
)
from backend.agent.cart_optimization_agent import build_cart_optimization_plan
from backend.agent.week_plan_agent import build_week_plan
from backend.core.pipeline import run_grocery_pipeline
from backend.core.gpt56_client import generate_primary_or_fallback
from auth import get_current_user
from backend.db.recipe_cache_repository import build_recipe_cache_key, list_recipes, save_recipe_cache, user_save_recipe
from backend.db.rate_limit_repository import (
    check_generate_limit,
    check_gemini_limit,
    check_chat_limit,
    increment_usage,
)
import base64
from backend.db.store_prices_repository import save_store_prices
from backend.db.pantry_repository import get_pantry, save_pantry

# ── Config ────────────────────────────────────────────────────────────────────
MCP_SERVER_URL = os.getenv(
    "MCP_SERVER_URL",
    "https://smartcart-mcp-505176174078.us-central1.run.app/mcp"
)

session_service = InMemorySessionService()
APP_NAME = "smartcart"
runner = None


# ── MCP helper (proper MCP protocol) ────────────────────────────────────────
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


# ── App ──────────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Smart Grocery AI",
    version="1.0.0",
    redirect_slashes=False,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://buildweek-smartcart.web.app",
        "https://qwen-smartcart.web.app",
        "https://smartcart-ai-dev.web.app",
        "http://localhost:3000",
        ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Models ───────────────────────────────────────────────────────────────────
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
    manual_city: str | None = None
    manual_state: str | None = None
    manual_postal_code: str | None = None
    force_refresh: bool = False

class ChatRequest(BaseModel):
    session_id: str = "default"
    message:    str

class CartOptimizationRequest(BaseModel):
    shopping_list: List[str]
    substitutions: Dict[str, object] = {}
    budget: float = 100

class PlanMyWeekRequest(BaseModel):
    budget: float = 100
    dietary_instruction: str = "Vegetarian only"
    meal_count: int = 21
    user_lat: float | None = None
    user_lng: float | None = None
    manual_city: str | None = None
    manual_state: str | None = None
    manual_postal_code: str | None = None

class SuggestedMeal(BaseModel):
    name: str | None = None
    reason: str | None = None
    title: str | None = None
    description: str | None = None
    meal: str | None = None
    why: str | None = None

class ShoppingListItem(BaseModel):
    name: str | None = None
    item: str | None = None
    title: str | None = None

class PlanMyWeekApproveRequest(BaseModel):
    suggested_meals: List[SuggestedMeal] | Dict[str, str | SuggestedMeal] | None = None
    combined_shopping_list: List[str | ShoppingListItem] | Dict[str, str | float | int | ShoppingListItem] | None = None
    weekly_meals: Dict[str, str] | None = None
    shopping_list: List[str | ShoppingListItem] | Dict[str, str | float | int | ShoppingListItem] | None = None
    budget_summary: Dict[str, object] = {}
    nutrition_report: Dict[str, object] = {}
    meal_ingredients: Dict[str, List[str]] = {}
    dietary_instruction: str = "Vegetarian only"

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


def _text_or_empty(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _model_fields(value: object) -> dict:
    if isinstance(value, BaseModel):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
    if isinstance(value, dict):
        return value
    return {}


def _meal_type_lookup(raw_meals: object) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    if isinstance(raw_meals, list):
        for meal in raw_meals:
            fields = _model_fields(meal)
            title = _text_or_empty(fields.get("name") or fields.get("title") or fields.get("meal"))
            meal_type = _meal_type_from_slot(fields.get("meal_type") or fields.get("mealType") or fields.get("type"))
            if title and meal_type:
                lookup[title] = meal_type
    elif isinstance(raw_meals, dict):
        for key, value in raw_meals.items():
            fields = _model_fields(value)
            meal_type = _meal_type_from_slot(key) or _meal_type_from_slot(fields.get("meal_type") or fields.get("mealType") or fields.get("type"))
            title = _text_or_empty(fields.get("name") or fields.get("title") or fields.get("meal") or value)
            if title and meal_type:
                lookup[title] = meal_type
            if key and meal_type:
                lookup[_text_or_empty(key)] = meal_type
    return lookup


def _normalize_weekly_meals(raw_meals: object) -> Dict[str, str]:
    normalized: Dict[str, str] = {}

    if isinstance(raw_meals, list):
        for meal in raw_meals:
            fields = _model_fields(meal)
            title = _text_or_empty(
                fields.get("name") or fields.get("title") or fields.get("meal")
            )
            description = _text_or_empty(
                fields.get("reason") or fields.get("description") or fields.get("why")
            )
            if title:
                normalized[title] = description or "Suggested for the week."
        return normalized

    if isinstance(raw_meals, dict):
        for key, value in raw_meals.items():
            fields = _model_fields(value)
            if fields:
                title = _text_or_empty(
                    fields.get("name") or fields.get("title") or fields.get("meal") or key
                )
                description = _text_or_empty(
                    fields.get("reason") or fields.get("description") or fields.get("why")
                )
                if title:
                    normalized[title] = description or "Suggested for the week."
            else:
                title = _text_or_empty(key)
                description = _text_or_empty(value)
                if title and description:
                    normalized[title] = description

    return normalized


def _meal_type_from_slot(slot: str | None) -> str:
    normalized = " ".join((slot or "").strip().lower().split())
    for meal_type in ("breakfast", "lunch", "dinner"):
        if meal_type in normalized.split():
            return meal_type
    return normalized if normalized in {"breakfast", "lunch", "dinner"} else ""


def _normalize_shopping_list(raw_items: object) -> List[str]:
    if isinstance(raw_items, dict):
        raw_items = list(raw_items.keys())
    if not isinstance(raw_items, list):
        return []

    normalized: List[str] = []
    seen = set()
    for item in raw_items:
        fields = _model_fields(item)
        if fields:
            value = _text_or_empty(fields.get("name") or fields.get("item") or fields.get("title"))
        else:
            value = _text_or_empty(item)
        key = value.lower()
        if value and key not in seen:
            normalized.append(value)
            seen.add(key)
    return normalized


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


# ── Routes ───────────────────────────────────────────────────────────────
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

        # ── Rate limit: Places API (every /generate) ─────────────────
        gen_check = check_generate_limit(uid)
        if not gen_check["allowed"]:
            raise HTTPException(status_code=429, detail=gen_check["message"])

        # ── Rate limit: Gemini (cache miss only) ─────────────────────
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
            manual_city=request.manual_city,
            manual_state=request.manual_state,
            manual_postal_code=request.manual_postal_code,
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


@app.post("/plan-my-week")
def plan_my_week(request: PlanMyWeekRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]
    print(f"[plan-my-week] request received for user={uid}")
    try:
        if request.meal_count < 1 or request.meal_count > 21:
            raise HTTPException(status_code=400, detail="meal_count must be between 1 and 21")

        gemini_check = check_gemini_limit(uid)
        result = build_week_plan(
            user_id=uid,
            budget=request.budget,
            dietary_instruction=request.dietary_instruction,
            user_lat=request.user_lat,
            user_lng=request.user_lng,
            manual_city=request.manual_city,
            manual_state=request.manual_state,
            manual_postal_code=request.manual_postal_code,
            meal_count=request.meal_count,
            gemini_allowed=gemini_check["allowed"],
        )
        if result.get("_gemini_called"):
            increment_usage(uid, "gemini")
        return result
    except HTTPException:
        raise
    except ValueError as e:
        print(f"[plan-my-week] bad request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"[plan-my-week] failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/plan-my-week/approve")
def approve_week_plan(request: PlanMyWeekApproveRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]
    print(f"[plan-my-week] approve received for user={uid}")
    try:
        raw_weekly_meals = request.suggested_meals if request.suggested_meals is not None else request.weekly_meals
        raw_shopping_list = request.combined_shopping_list if request.combined_shopping_list is not None else request.shopping_list
        weekly_meals = _normalize_weekly_meals(raw_weekly_meals)
        meal_type_lookup = _meal_type_lookup(raw_weekly_meals)
        shopping_list = _normalize_shopping_list(raw_shopping_list)

        if not weekly_meals:
            raise HTTPException(status_code=400, detail="weekly_meals or suggested_meals is required")
        if not shopping_list:
            raise HTTPException(status_code=400, detail="shopping_list or combined_shopping_list is required")

        saved = []
        meal_ingredients = request.meal_ingredients or {}
        for meal_key, description in weekly_meals.items():
            slot_meal_type = _meal_type_from_slot(meal_key)
            meal_type = meal_type_lookup.get(meal_key) or slot_meal_type
            meal_name = description if slot_meal_type and description else meal_key
            ingredients = meal_ingredients.get(meal_name) or meal_ingredients.get(meal_key) or shopping_list
            cache_key = build_recipe_cache_key(meal_name, request.dietary_instruction)
            saved.append(save_recipe_cache(
                user_id=uid,
                meal=cache_key,
                ingredients=ingredients,
                source="approved_week_plan",
                nutrition=request.nutrition_report,
                meal_type=meal_type,
            ))
        return {"success": True, "saved": saved}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[plan-my-week] approve failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/optimize-cart-agent")
async def optimize_cart_agent(request: CartOptimizationRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]
    print(f"[optimize-cart-agent] request received for user={uid}")
    try:
        return build_cart_optimization_plan(
            user_id=uid,
            shopping_list=request.shopping_list,
            substitutions=request.substitutions,
            budget=request.budget,
        )
    except ValueError as e:
        print(f"[optimize-cart-agent] bad request: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        print(f"[optimize-cart-agent] failed: {e}")
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/chat")
async def chat(req: ChatRequest, user: dict = Depends(get_current_user)):
    uid = user["uid"]

    # ── Rate limit: chat ─────────────────────────────────────────────
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

    # Gemini is primary for this build — OPENAI_API_KEY is intentionally unset
    # so generate_primary_or_fallback() always routes to Gemini via fast-fail.
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
def _normalize_pantry_items(raw_items) -> list[str]:
    if raw_items is None:
        return []
    if not isinstance(raw_items, list):
        raise HTTPException(status_code=400, detail="items must be a list")

    normalized = []
    seen = set()
    for item in raw_items:
        if isinstance(item, str):
            value = item.strip().lower()
        elif isinstance(item, dict):
            value = str(item.get("name") or item.get("item") or "").strip().lower()
        else:
            continue
        if value and value not in seen:
            normalized.append(value)
            seen.add(value)
    return normalized


@app.get("/debug/pantry/me")
async def debug_pantry_me(user: dict = Depends(get_current_user)):
    uid = user["uid"]
    try:
        items = get_pantry(uid)
        return {"result": {"user_id": uid, "items": items, "count": len(items)}, "success": True}
    except Exception as e:
        print(f"[debug_pantry_me] failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/pantry")
async def update_pantry(body: dict, user: dict = Depends(get_current_user)):
    uid = user["uid"]  # verified, not from URL
    items = _normalize_pantry_items(body.get("items", []))
    print(f"[pantry] updating {uid}: {items}")
    try:
        result = save_pantry(uid, items)
        print(f"[update_pantry] result: {result}")
        return {"result": result, "success": True}
    except Exception as e:
        print(f"[update_pantry] failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    Upload a grocery receipt photo or PDF, parse item prices, and save them to
    shared city-level Firestore price docs.
    """
    from vertexai.generative_models import GenerativeModel, Part as VPart

    uid = user["uid"]
    print(f"[receipt/upload] received upload user={uid} media_type={body.media_type} city={body.city!r} state={body.state!r}")

    try:
        try:
            image_bytes = base64.b64decode(body.image_base64)
        except Exception:
            print("[receipt/upload] invalid base64 payload")
            raise HTTPException(status_code=400, detail="Invalid base64 image data")

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

        import vertexai
        vertexai.init(project=os.getenv("GOOGLE_PROJECT_ID"), location="us-central1")
        model = GenerativeModel(os.getenv("GEMINI_MODEL_NAME", "gemini-2.5-flash"))

        media_type = body.media_type
        part = VPart.from_data(
            data=image_bytes,
            mime_type="application/pdf" if media_type == "application/pdf" else media_type,
        )

        response = model.generate_content([part, prompt])
        text = response.text.strip()
        if "```" in text:
            text = text.split("```")[1]
            if text.lower().startswith("json"):
                text = text[4:]
            text = text.strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as e:
            print(f"[receipt/upload] parse failed: {e}; raw={text[:500]}")
            raise HTTPException(status_code=422, detail=f"Could not parse receipt. Try a clearer photo. ({e})")

        store_name = body.store_name.strip() or parsed.get("store_name", "").strip() or "Unknown Store"
        city = body.city.strip()
        state = body.state.strip()
        country = body.country.strip() or "US"
        address = body.address.strip()
        receipt_date = body.receipt_date.strip() or parsed.get("receipt_date", "")
        items = parsed.get("items", {})
        print(f"[receipt/upload] parsed store={store_name!r} item_count={len(items) if isinstance(items, dict) else 'invalid'} preview={dict(list(items.items())[:3]) if isinstance(items, dict) else items}")

        if not isinstance(items, dict) or not items:
            raise HTTPException(status_code=422, detail="No items found in receipt. Please try a clearer photo.")

        if not city or not state:
            print(f"[receipt/upload] missing city/state city={city!r} state={state!r}")
            raise HTTPException(status_code=400, detail="Could not determine store location. Please enter city and state.")

        print(f"[receipt/upload] saving receipt prices city={city!r} state={state!r} country={country!r}")
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
        print(f"[receipt/upload] Firestore write result: {result}")

        return {
            "success": True,
            "store_name": store_name,
            "city": result["city"],
            "state": result["state"],
            "item_count": result["item_count"],
            "items_preview": result["items_preview"],
            "store_id": result["store_id"],
            "city_key": result["city_key"],
            "sample_path": result["sample_path"],
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
        print(f"[receipt/stores] failed city={city!r} state={state!r}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
