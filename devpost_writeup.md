# SmartCart AI

---

## Inspiration

Every week, millions of people face the same frustrating cycle: decide what to cook, figure out what ingredients to buy, check what's already in the pantry, stay within budget, and then navigate multiple stores. It's exhausting — and expensive when done poorly.

We wanted to build something that collapses this entire workflow into a single AI-powered interaction. Tell it what you want to eat. Get everything else handled automatically.

---

## What It Does

SmartCart AI turns meal planning and grocery shopping into a single conversational, pantry-aware experience.

Instead of manually planning meals, checking your pantry, comparing stores, and optimizing routes, users simply talk to the system. It understands what they have, what they need, and what they can cook — and then generates a complete personalized grocery and meal plan.

## Core capabilities:
- Builds full ingredient lists from a meal or weekly plan
- Pantry-aware chatbot that can inspect inventory and generate recipes from available ingredients
- Removes items already available in the user’s pantry
- Suggests meals like “What can I cook with rice and oil?” using partial pantry inputs
- Finds the best nearby grocery stores based on location
- Optimizes multi-store shopping routes
- Provides nutrition insights for planned meals
- Suggests dietary-aware ingredient substitutions
- Remembers user preferences for future sessions
- Allows regeneration of plans with substitutions applied

The result is a single end-to-end assistant that replaces multiple apps and manual steps with one intelligent workflow.

---

## Agent Workflow 

1. User submits a meal request, grocery list, or weekly meal plan.
2. Request is received by the React frontend and sent to the FastAPI backend.
3. Google ADK agent orchestrates the planning workflow.
4. MCP server is queried for cached recipes via MongoDB Atlas.
5. If cache hit → return stored meal plan, nutrition data, and substitutions.
6. If cache miss → Gemini 2.5 Flash generates:
   - Ingredient list
   - Nutrition breakdown
   - Substitution suggestions
7. MCP tool retrieves pantry inventory from MongoDB Atlas.
8. Pantry-aware logic filters available ingredients and adjusts meal generation accordingly.
9. Google Maps API is used to discover nearby grocery stores.
10. Store options are evaluated and an optimized shopping route is generated.
11. Dietary preferences and substitutions are applied if provided by the user.
12. Final plan is persisted via MCP tools:
    - Meal plan
    - Pantry updates
    - Cached recipe data
13. Response is returned to frontend with:
    - Final shopping list
    - Store recommendations
    - Optimized route
    - Nutrition analysis
    - Budget breakdown
    - Substitution suggestions
    
---

## How We Built It

**Frontend** — React app hosted on Firebase Hosting with a tabbed results interface: Shopping List, Store Prices, Route, Nutrition, Substitutions, and Budget.

**Backend** — FastAPI on Google Cloud Run, orchestrating a 10-step AI pipeline.

**AI** — Google Gemini 2.5 Flash via Vertex AI generates shopping lists, nutrition analysis, and substitution recommendations in a single structured JSON prompt.

**MCP Integration** — FastMCP (Model Context Protocol) connects the agent to MongoDB Atlas for pantry management and recipe caching. The agent uses MCP tools to read pantry items and persist user preferences.

**Smart Caching** — MongoDB Atlas caches shopping lists, substitutions, and nutrition reports per recipe. On repeat requests for the same meal, data is served directly from MongoDB — no Gemini API call is made — significantly reducing token costs. Cache keys are normalized to handle spacing and casing variations.

**Maps & Location** — Google Maps API powers store discovery and route optimization based on the user's live GPS location.

---

## Architecture:

```
                    ┌────────────────────────────┐
                    │        React UI            │
                    │   (Firebase Hosting)       │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │     FastAPI Backend        │
                    │  (Request Orchestrator)    │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌────────────────────────────┐
                    │    Google ADK Agent        │
                    │ (Reasoning + Tool Router)  │
                    └───────┬─────────┬──────────┘
                            │         │
          ┌─────────────────┘         └────────────────────┐
          ▼                                                ▼
┌───────────────────────┐                    ┌────────────────────────┐
│     MCP Server        │                    │   Gemini 2.5 Flash     │
│  (Tools + Memory)     │                    │  (Reasoning Engine)    │
│                       │                    │                        │
│ - pantry tools        │                    │ - meal generation      │
│ - caching             │                    │ - nutrition analysis   │
│ - persistence         │                    │ - substitutions        │
└──────────┬────────────┘                    └──────────┬─────────────┘
           │                                            │
           ▼                                            │
┌────────────────────────────┐                          │
│     MongoDB Atlas          │◄─────────────────────────┘
│  (State + Cache Layer)     │
└────────────────────────────┘


           ▼
┌────────────────────────────┐
│     Google Maps API        │
│ (Stores + Route Optimizer) │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│   Response Composer        │
│ (Final Aggregation Layer)  │
└────────────┬───────────────┘
             ▼
┌────────────────────────────┐
│        React UI            │
│ Tabs: List / Route / etc   │
└────────────────────────────┘

```

---

## Tech Stack:

- Google ADK — agent orchestration, tool calling, session management
- Gemini 2.5 Flash on Vertex AI — meal plan generation, nutrition analysis, substitution suggestions
- FastMCP (Python) — custom MCP server exposing pantry, meal plan, and recipe cache tools
- MongoDB Atlas — persistent storage for pantry inventory, meal plans, and recipe cache
- FastAPI — backend pipeline for store pricing, route optimization, and budget analysis
- React — frontend UI with 6 result tabs
- Google Cloud Run — serverless deployment for ADK agent, MCP server, and FastAPI backend
- Firebase Hosting — React frontend deployment
- Google Maps API — store location and route optimization

---

## MCP Tools exposed:

- get_pantry_items — fetches user’s current pantry from MongoDB
- save_meal_plan_tool — persists generated meal plan and shopping list
- get_recipe_cache — checks if a recipe was previously generated
- save_recipe_cache_tool — caches new recipes to avoid redundant Gemini calls
- ping — health check

---

## Why MCP

Rather than allowing the agent to directly access MongoDB Atlas, we exposed pantry management, recipe caching, and meal plan persistence through a custom FastMCP server.

This gives the Google ADK agent a standardized tool interface for interacting with external data. The agent can dynamically discover and invoke tools without needing database-specific logic, keeping the AI reasoning layer separate from the persistence layer.

Using MCP also makes the system more extensible. New capabilities can be added as tools without modifying the agent's core workflow. For example, future integrations such as barcode scanning, grocery price feeds, or inventory notifications can be exposed through the same MCP interface.

This architecture enables persistent memory, reusable tooling, and clean separation between agent reasoning and backend services.


---

## The MCP Integration
The heart of SmartCart AI is the MCP server running as a standalone Cloud Run service. The ADK agent connects to it via Streamable HTTP — the modern MCP transport protocol. Every time a user asks about their pantry or saves a meal plan, the agent calls the MCP server which handles all MongoDB operations. This separation of concerns means the AI layer stays clean while the data layer stays persistent and reusable.

The recipe cache tool is particularly powerful — if Gemini already generated a recipe for “Lentil Curry” previously, the MCP server returns the cached result directly instead of making a new Gemini call. This eliminates redundant model inference, reduces operational costs, and improves the user experience for repeat recipe requests.

---

## Challenges We Ran Into

- **MCP session management on Cloud Run** — streamable HTTP sessions expire between calls on serverless infrastructure. Solved with --min-instances=1 to keep the instance warm and the session alive.
- **ADK + asyncio conflict** — the MCP client’s anyio task scoping conflicts with uvicorn’s event loop when creating a new agent per request. Solved by initializing the runner once at startup using FastAPI’s lifespan context manager.
- **MCP Protocol Debugging** — Getting FastMCP's JSON-RPC handshake and SSE response parsing to work correctly on Cloud Run required careful host header configuration.
- **Cache Invalidation** — After a user saves substitution preferences, the cache needs to update with the personalized ingredient list without wiping out nutrition and substitution data saved from the original Gemini call.

---

## Accomplishments

- Built a production-ready AI agent using Google ADK, Gemini, MCP, and Cloud Run
- Designed a custom FastMCP server exposing pantry, caching, and persistence tools to the ADK agent
- Eliminated redundant Gemini API calls for repeat recipes through MongoDB-backed caching, significantly reducing response time and token consumption
- Implemented personalized grocery planning based on pantry inventory and dietary preferences
- Deployed the entire system serverlessly on Google Cloud

---

## What We Learned

- Google ADK’s MCPToolset with StreamableHTTPConnectionParams is powerful but requires careful async initialization — per-request agent creation causes task scope errors in production
- FastMCP makes building MCP servers in Python remarkably straightforward — the @mcp.tool() decorator auto-generates JSON schemas from type hints
- The lifespan pattern in FastAPI is the right way to manage long-lived connections like MCP toolsets in a serverless environment
- MCP is a powerful pattern for connecting AI agents to external data sources — but protocol-level debugging requires careful attention to transport layer details.
- Prompt engineering is as important as architecture. Small changes to output format instructions have outsized impact on response quality.
- Caching at the right layer (full response, not just ingredients) is critical for both cost efficiency and user experience.
- ADK on Vertex AI requires specific environment variables (GOOGLE_CLOUD_LOCATION, GOOGLE_GENAI_USE_VERTEXAI) rather than just a project ID. Required careful debugging of the model resolution path.
- Shopping list items and substitution keys had inconsistent casing and formatting. Solved with case-insensitive partial matching.
- Using `0` as placeholder values in the nutrition prompt caused Gemini to literally return zeros. Replaced with descriptive placeholders to get accurate estimated values.
- Extra whitespace in meal names caused `update_one` upserts to miss existing records and insert duplicates. Fixed with space normalization across all cache key builders.

---

## What's Next

- **User account authentication** — Authentication and multi-device profile synchronization
- **Barcode scanning** — Auto-add pantry items by scanning receipts or product barcodes
- **Family profiles** — Multi-user dietary preferences in a single household plan
- **Voice inputs** — "Hey SmartCart, plan my week"
- **Real-time Price tracking** — Real-time store price integration via Google Shopping API
- **Notification on expiring items** - Reminder for grocery expiring in 3 days based on items in the pantry
- **Customized Recipe caching** – Cache recipes with a customize option in the database to avoid redundant calls to Gemini

---

## Built With

`google-gemini` `vertex-ai` `google-cloud-run` `firebase` `fastapi` `python` `react` `mongodb-atlas` `fastmcp` `google-maps-api` `google-cloud-build` `docker`

---

## Links

- 🌐 Live App: https://hackathon-grocery-ai-498023.web.app
- 💻 GitHub: https://github.com/shobanasreedharan/SmartCartAI
- 🎥 Demo Video: [YOUR DEMO VIDEO URL]
