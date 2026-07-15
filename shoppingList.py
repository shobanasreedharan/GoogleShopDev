from typing import Dict, Any
from google import genai
from google.genai import types
from dotenv import load_dotenv
import os

load_dotenv()

print(os.getenv("GOOGLE_API_KEY"))


# ---------------------------------------------------------
# Step 1: Define the core Agent/Tool functions
# ---------------------------------------------------------

def understand_dish(dish_name: str) -> Dict[str, Any]:
    """
    Analyzes the requested dish name to determine its culinary style,
    approximate preparation time, and overall profile.
    """
    # In a production app, this could query a database or API.
    # For this agent, it acts as a structured validation wrapper.
    print(f"\n[Tool Execution] Running understand_dish for: '{dish_name}'")
    return {
        "dish_name": dish_name.strip(),
        "status": "Validated",
        "notes": f"Identified as a standard preparation path for {dish_name}."
    }


def generate_ingredients(dish_name: str, servings: int = 4) -> Dict[str, Any]:
    """
    Generates a structured dictionary list of ingredients and their base metrics
    required to prepare the specified dish.
    """
    print(f"[Tool Execution] Running generate_ingredients for: '{dish_name}' ({servings} servings)")

    # We provide a fallback mock dictionary, but the LLM will map out the payload
    return {
        "dish": dish_name,
        "servings": servings,
        "ingredients_generated": True
    }


def create_shopping_list(ingredients_list: str) -> Dict[str, Any]:
    """
    Consolidates a raw string list of ingredients into an optimized,
    aisle-categorized grocery shopping list.
    """
    print(f"[Tool Execution] Running create_shopping_list")
    return {
        "shopping_list_ready": True,
        "raw_input_received": ingredients_list[:50] + "..." if len(ingredients_list) > 50 else ingredients_list
    }


# ---------------------------------------------------------
# Step 2: Orchestration Loop
# ---------------------------------------------------------

def run_recipe_agent(user_prompt: str):
    """
    Initializes the Gemini Client and uses auto-function orchestration
    to loop through your local python steps automatically.
    """
    # Ensure you have your environment variable set: export GEMINI_API_KEY="your-api-key"
    if not os.environ.get("GOOGLE_API_KEY"):
        raise ValueError("Please set your GOOGLE_API_KEY environment variable.")

    client = genai.Client()

    # Bundle the local Python functions into the tools array
    my_tools = [understand_dish, generate_ingredients, create_shopping_list]

    # Instruct the agent on its sequential goals
    system_instruction = (
        "You are an expert Culinary Agent. When a user asks for a dish recipe or list, "
        "you MUST step-by-step invoke: \n"
        "1. understand_dish to log/validate the meal.\n"
        "2. generate_ingredients to layout what is needed.\n"
        "3. create_shopping_list to format the grocery layout.\n"
        "Execute these tools sequentially to compile your data before giving your final answer."
    )

    print(f"User Request: {user_prompt}")
    print("Initializing Gemini Agent workflow...")

    # The Modern SDK automatically handles the back-and-forth loops
    # to run your local python functions when tools=[] is supplied.
    response = client.models.generate_content(
        model="gemini-3.1-flash-lite",
        contents=user_prompt,
        config=types.GenerateContentConfig(
            system_instruction=system_instruction,
            tools=my_tools,
            temperature=0.2  # Lower temperature keeps execution deterministic
        )
    )

    print("\n================ FINAL AGENT OUTPUT ================")
    print(response.text)
    print("====================================================")


if __name__ == "__main__":
    # Test example
    sample_request = "2 veg samosa"
    run_recipe_agent(sample_request)