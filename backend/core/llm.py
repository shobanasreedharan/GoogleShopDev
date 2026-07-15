import json
import vertexai
from vertexai.generative_models import GenerativeModel

import os
from dotenv import load_dotenv
load_dotenv()

PROJECT_ID = os.getenv("GOOGLE_PROJECT_ID")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME")

class GeminiPlanner:

    def decide_next_action(self, state):

        prompt = f"""
You are a grocery AI agent.

Current state:
{json.dumps(state, indent=2)}

Choose ONE action:
- GET_INGREDIENTS
- CHECK_PANTRY
- OPTIMIZE_BUDGET
- FIND_STORES
- ROUTE
- FINALIZE

Return JSON:
{{
  "type": "ACTION_NAME"
}}
"""

        vertexai.init(
            project=PROJECT_ID,
            location="us-central1"
        )

        model = GenerativeModel(GEMINI_MODEL_NAME)

        response = model.generate_content(prompt)


        try:
            return json.loads(response)
        except:
            return {"type": "FINALIZE"}