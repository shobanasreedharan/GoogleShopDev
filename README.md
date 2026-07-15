# SmartCart AI 🛒
### AI-Powered Grocery Intelligence

> Built for the Google Cloud Rapid Agent Hackathon 2026

SmartCart AI is an intelligent grocery planning agent that transforms your meal ideas into optimized shopping plans — complete with store recommendations, route optimization, nutritional analysis, and smart substitutions.

---

## Live Demo

 [https://hackathon-grocery-ai-498023.web.app](https://hackathon-grocery-ai-498023.web.app)

---

## Problem Statement

Planning meals and grocery shopping can be time-consuming and expensive.
Users often struggle with:

- Creating ingredient lists from scratch
- Maintaining balanced nutrition across the week
- Staying within a grocery budget
- Finding ingredient substitutions for dietary needs or unavailable items
- Choosing the best stores for price and convenience

**SmartCart AI automates the entire workflow** — from meal idea to optimized shopping plan in seconds.

---

## Features

- **Meal to Shopping List** — Enter any meal or weekly plan; the AI generates a complete ingredient list
- **Smart Substitutions** — Choose ingredient alternatives based on dietary preference or availability
- **Nearby Store Finder** — Locates the best stores near you with availability scores
- **Route Optimization** — Plans the most efficient shopping route across stores
- **Nutrition Analysis** — Full macro breakdown with AI health feedback
- **Budget Optimizer** — Estimates costs and finds savings across stores
- **Personalized Cache** — Remembers your substitution preferences for future plans
- **Dietary Modes** — Supports Vegetarian, Vegan, Gluten-Free, and more

---

## Smart Caching Strategy

SmartCart AI uses MongoDB as an intelligent cache to minimize AI token costs:

- On the **first request** for a recipe, Gemini generates the shopping list, substitutions, and nutrition report — all three are saved to MongoDB.
- On **subsequent requests** for the same recipe, data is pulled directly from MongoDB — **no Gemini call is made**, saving token costs entirely.
- When a user **saves substitution preferences**, the cache is updated with the personalized ingredient list so future plans reflect their choices automatically.
- Cache keys are normalized (lowercase, collapsed spaces) so `"Creamy Tomato Soup"` and `"creamy tomato  soup"` always resolve to the same record.

This means the more the app is used, the cheaper and faster it gets

---

##  Architecture

```
┌─────────────────────────────────────────────┐
│              React Frontend                 │
│         (Firebase Hosting)                  │
└─────────────────┬───────────────────────────┘
                  │ REST API
┌─────────────────▼───────────────────────────┐
│           FastAPI Backend                   │
│         (Google Cloud Run)                  │
│                                             │
│  ┌──────────────────────────────────────┐   │
│  │         10-Step AI Pipeline          │   │
│  │  1. Unified AI Agent (Gemini 2.5)    │   │
│  │  2. Shopping List Compiler           │   │
│  │  3. Substitution Persistence         │   │
│  │  4. Pantry Filter                    │   │
│  │  5. Budget Optimizer                 │   │
│  │  6. Location Resolver                │   │
│  │  7. Store Finder (Google Maps)       │   │
│  │  8. Route Optimizer                  │   │
│  │  9. MongoDB Save                     │   │
│  │  10. Response Formatter              │   │
│  └──────────────────────────────────────┘   │
└─────────────────┬───────────────────────────┘
                  │
┌─────────────────▼───────────────────────────┐
│           MongoDB Atlas                     │
│   recipe_cache | meal_plans | pantry        │
└─────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React, Firebase Hosting |
| Backend | FastAPI, Python |
| AI | Google Gemini 2.5 Flash via Vertex AI |
| MCP | FastMCP (Model Context Protocol) |
| Database | MongoDB Atlas |
| Infrastructure | Google Cloud Run, Google Container Registry |
| Maps | Google Maps API |

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- Google Cloud SDK
- MongoDB Atlas account

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload --port 8080
```

### Frontend
```bash
cd smartcart-ui
npm install
npm start
```

### Environment Variables
```env
MDB_MCP_CONNECTION_STRING=mongodb+srv://...
MONGO_DB=smart_grocery
GOOGLE_CLOUD_PROJECT=your-project-id
GEMINI_MODEL_NAME=gemini-2.5-flash
GOOGLE_GENAI_USE_VERTEXAI=true
GOOGLE_CLOUD_LOCATION=us-central1
GOOGLE_MAPS_API_KEY=your-maps-api-key
```

> ⚠️ Never commit `.env` files or API keys to the repository.

---

## Project Structure

```
smartcart-ai/
├── backend/
│   ├── agent/          # Unified AI agent (Gemini)
│   ├── core/           # MCP registry
│   ├── db/             # MongoDB repositories
│   ├── optimization/   # Budget + route optimizers
│   ├── schemas/        # Pydantic models
│   ├── services/       # Store finder, location
│   ├── utils/          # Sanitizers, helpers
│   └── validators/     # Nutrition validator
├── smartcart-ui/       # React frontend
│   └── src/
│       └── SmartCartAI.jsx
├── README.md
└── LICENSE
```

---

## Hackathon

Built for the **Google Cloud Rapid Agent Hackathon 2026** by Shobana Sreedharan.

---

## License

© 2026 Shobana Sreedharan. All rights reserved.

This project is publicly viewable for portfolio and demonstration purposes only.
**Commercial use is strictly prohibited.** See [LICENSE](./LICENSE) for full terms.

---

## Author

**Shobana Sreedharan**

- [email](shobana.sreedharan@gmail.com)

- [LinkedIn](https://www.linkedin.com/in/shobana-sreedharan-4711801a/)

