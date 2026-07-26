# SmartCart AI - A Kitchen Operating System

**AI-powered kitchen operating system that turns your pantry into a week of meals, a smart budget, and the cheapest store run nearby.**

Built for OpenAI Build Week. Originally created as SmartCart AI for the Google Cloud Rapid Agent Hackathon, and rebuilt for the Alibaba/Qwen Cloud Hackathon — this submission is the third iteration of the same codebase, now rearchitected as a genuinely autonomous AI agent.

🔗 **Live app:** https://buildweek-smartcart.web.app

---

## What it does

SmartCart AI offers two agent modes:

- **Plan My Week** — fully autonomous. No preferences required. The agent chains five tools in a single run: checks your pantry, generates a week of meals, builds a shopping list, optimizes your budget, and compares real nearby grocery stores to find the cheapest one — all without mid-flow user input.
- **Optimize My Cart** — generated when the user provides meal preferences. Runs the same pantry/budget/substitution/store-comparison tools, shaped around what the user actually wants to eat.

Every tool call the agent makes is visible via **AgentTrace**, so the reasoning is never a black box. Clicking "Plan meal from my pantry" in chat shows the exact agent tool being invoked in real time.

---

## How GPT-5.6 and Codex were used

**GPT-5.6** is the primary AI model powering the agent pipeline — used for weekly meal generation, budget/substitution reasoning, and nutrition feedback via `generate_primary_or_fallback()` in `backend/core/gpt56_client.py`. If GPT-5.6 is unavailable, the app automatically fails over to Gemini so a single provider outage never breaks the experience.

**OpenAI Codex** was used throughout final development and debugging as a coding agent, working alongside Claude for planning and verification. Codex was responsible for:

- Diagnosing and fixing a Pydantic validation mismatch in `/plan-my-week/approve`, where the API expected a flat `{name: description}` dict but the actual generated data was a list of `{name, reason}` meal objects — Codex traced the real shape, added proper Pydantic models (`SuggestedMeal`), and wrote defensive normalization logic to accept multiple payload shapes.
- Rebuilding the store-recommendation pipeline (`backend/services/store_finder.py`) to filter nearby results down to actual grocery stores (excluding non-grocery places like gas stations and restaurants) and to price the real generated shopping list against each store, producing genuine per-store basket comparisons instead of placeholder data.
- Fixing a frontend display bug where FastAPI's structured validation errors were rendered as raw `[object Object]` text instead of readable messages, by writing an `apiErrorMessage()` helper that correctly parses FastAPI's error array format.
- Adding the "Compare Nearby Stores" UI section to the Plan My Week card, consuming the corrected store-comparison data and highlighting the cheapest option.
- Fixing a save-confirmation display bug where a successful save silently rendered as an empty error-styled box due to a string/object type mismatch in component state.

All Codex-authored changes were reviewed, tested end-to-end against the live deployed site, and verified by hand before being merged — several early Codex fixes were caught as incomplete or based on incorrect assumptions about data shape, and iterated on with more precise, evidence-based prompts (e.g. requiring Codex to print and inspect actual API response shapes rather than guess).

---

## Architecture

- **Frontend:** React, deployed to Firebase Hosting (multi-target setup across three hackathon submissions from one codebase)
- **Backend:** FastAPI on Google Cloud Run, containerized via Cloud Build and Artifact Registry
- **AI layer:** GPT-5.6 (primary) with automatic Gemini fallback
- **Data:** Firestore (user-scoped pantry, recipe cache, meal plans, receipts)
- **Auth:** Firebase Auth with Google Sign-In
- **Store pricing:** Real store-finder pipeline using location + Places data, filtered to grocery stores, pricing the actual generated shopping list per store

---

## Running locally

```bash
# Backend
py -m uvicorn backend.api.main:app --reload --port 8000

# Frontend
cd smartcart-ui
npm install
npm start
```

---

## License

This project is licensed for **non-commercial use only**. See [LICENSE](./LICENSE) for full terms.

Copyright © 2026 Shobana Sreedharan
