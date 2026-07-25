## Link to test the project

Live app: https://buildweek-smartcart.web.app

## Testing instructions

1. Click the login/sign-in button and sign in with any Google account (Firebase Auth / Google Sign-In — no special credentials needed, any Google account works).
2. Once signed in, click **"PLAN MY WEEK"** on the Plan My Week card. This runs the fully autonomous agent — no preferences or setup required. It will:
   - Check pantry (a small default pantry is available even for a fresh account)
   - Generate 5 meal suggestions
   - Build a combined shopping list
   - Optimize the budget
   - Compare real nearby grocery stores (uses your browser's approximate location — please allow location access, or fall back to city/ZIP entry if prompted)
3. Expand **"Agent Used Tools"** to see the full AgentTrace — each of the 5 tools the agent called, in order, with results.
4. Scroll down to **"Compare Nearby Stores"** to see real per-store pricing with the cheapest store highlighted.
5. Click **"Approve & Save"** to confirm the save flow (green confirmation message).
6. Optionally, in the chat panel, try typing or clicking **"Plan meal from my pantry"** to see the preference-driven **Optimize My Cart** path and the agent tool invocation shown live in chat.

No paid credentials or API keys are needed to test — everything runs against our deployed backend.

## Known limitations for judges

- Store prices are AI-generated estimates for most items; receipt-uploaded prices are used preferentially where available, and are marked as such in the price breakdown.
- Location-based store search defaults to the tester's actual approximate location (via browser geolocation); a manual city/ZIP entry is available as a fallback if location access is denied.
