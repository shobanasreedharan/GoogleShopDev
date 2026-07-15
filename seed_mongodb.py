"""
SmartCart AI — MongoDB Seed Script
====================================
Run once to populate your Atlas cluster with:
  - products     (60+ grocery items, 6 store prices each)
  - stores       (6 major US chains with coordinates)
  - users        (1 demo user)
  - meal_plans   (2 sample saved plans)

Usage:
  1. pip install --upgrade pymongo python-dotenv
  2. Confirm your .env has: MONGO_URI and MONGO_DB
  3. python seed_mongodb.py

Matches your existing mongo_client.py env var names.
"""

DB_NAME = "smart_grocery"  # matches MONGO_DB default in mongo_client.py

# -------------------------------------------------------

from pymongo import MongoClient  # removed unused GEOSPHERE import
from dotenv import load_dotenv
from datetime import datetime, timezone
import os
import sys

load_dotenv()

MONGODB_URI = os.getenv("MONGO_URI")   # matches your mongo_client.py

if not MONGODB_URI:
    print("❌ MONGO_URI not found in .env file")
    print("   Add this to your .env:")
    print('   MONGO_URI="mongodb+srv://<user>:<pass>@<cluster>.mongodb.net/"')
    print('   MONGO_DB="smart_grocery"')
    sys.exit(1)


# =====================================================
# CONNECT
# =====================================================

def get_db():
    client = MongoClient(MONGODB_URI)
    db = client[DB_NAME]
    #print(f"✅ Connected to MongoDB Atlas → {DB_NAME}")
    return db


# =====================================================
# PRODUCTS COLLECTION
# 60+ vegetarian grocery items
# Prices for: Walmart, Kroger, ALDI, Whole Foods,
#             Trader Joe's, Costco
# Price reflects realistic 2025 US grocery prices
# =====================================================

PRODUCTS = [

    # ── VEGETABLES ─────────────────────────────────
    {
        "name": "tomatoes",
        "category": "vegetables",
        "unit": "1 lb",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.49,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      5.99,   # bulk 3 lb
        }
    },
    {
        "name": "onions",
        "category": "vegetables",
        "unit": "2 lb bag",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     1.78,
            "Kroger":      1.99,
            "ALDI":        1.29,
            "Whole Foods": 2.99,
            "Trader Joe's":1.99,
            "Costco":      4.99,
        }
    },
    {
        "name": "garlic",
        "category": "vegetables",
        "unit": "3 bulb pack",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.88,
            "Kroger":      0.99,
            "ALDI":        0.69,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      3.99,
        }
    },
    {
        "name": "spinach",
        "category": "vegetables",
        "unit": "5 oz bag",
        "tags": ["fresh", "produce", "leafy greens"],
        "prices": {
            "Walmart":     2.98,
            "Kroger":      3.49,
            "ALDI":        2.19,
            "Whole Foods": 3.99,
            "Trader Joe's":2.99,
            "Costco":      6.99,
        }
    },
    {
        "name": "broccoli",
        "category": "vegetables",
        "unit": "1 head",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     1.28,
            "Kroger":      1.49,
            "ALDI":        0.99,
            "Whole Foods": 2.49,
            "Trader Joe's":1.99,
            "Costco":      4.99,
        }
    },
    {
        "name": "bell pepper",
        "category": "vegetables",
        "unit": "1 each",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.98,
            "Kroger":      1.29,
            "ALDI":        0.79,
            "Whole Foods": 1.99,
            "Trader Joe's":1.49,
            "Costco":      5.99,   # 6 pack
        }
    },
    {
        "name": "carrot",
        "category": "vegetables",
        "unit": "1 lb bag",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.98,
            "Kroger":      1.29,
            "ALDI":        0.79,
            "Whole Foods": 1.99,
            "Trader Joe's":1.29,
            "Costco":      3.99,
        }
    },
    {
        "name": "mushrooms",
        "category": "vegetables",
        "unit": "8 oz pack",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.69,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      5.99,
        }
    },
    {
        "name": "zucchini",
        "category": "vegetables",
        "unit": "1 each",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.88,
            "Kroger":      0.99,
            "ALDI":        0.69,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      4.99,
        }
    },
    {
        "name": "kale",
        "category": "vegetables",
        "unit": "1 bunch",
        "tags": ["fresh", "produce", "leafy greens"],
        "prices": {
            "Walmart":     1.48,
            "Kroger":      1.79,
            "ALDI":        1.19,
            "Whole Foods": 2.49,
            "Trader Joe's":1.99,
            "Costco":      5.49,
        }
    },
    {
        "name": "cauliflower",
        "category": "vegetables",
        "unit": "1 head",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     2.48,
            "Kroger":      2.99,
            "ALDI":        1.89,
            "Whole Foods": 3.99,
            "Trader Joe's":2.49,
            "Costco":      5.99,
        }
    },
    {
        "name": "sweet potato",
        "category": "vegetables",
        "unit": "1 lb",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.98,
            "Kroger":      1.29,
            "ALDI":        0.89,
            "Whole Foods": 1.99,
            "Trader Joe's":1.49,
            "Costco":      4.99,
        }
    },
    {
        "name": "cucumber",
        "category": "vegetables",
        "unit": "1 each",
        "tags": ["fresh", "produce"],
        "prices": {
            "Walmart":     0.68,
            "Kroger":      0.79,
            "ALDI":        0.59,
            "Whole Foods": 1.29,
            "Trader Joe's":0.99,
            "Costco":      3.99,
        }
    },

    # ── PROTEIN ────────────────────────────────────
    {
        "name": "tofu",
        "category": "protein",
        "unit": "14 oz block",
        "tags": ["plant protein"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.49,
            "ALDI":        1.79,
            "Whole Foods": 3.49,
            "Trader Joe's":2.29,
            "Costco":      9.99,   # 4 pack
        }
    },
    {
        "name": "black beans",
        "category": "protein",
        "unit": "15 oz can",
        "tags": ["canned", "plant protein"],
        "prices": {
            "Walmart":     0.88,
            "Kroger":      0.99,
            "ALDI":        0.69,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      8.99,   # 12 pack
        }
    },
    {
        "name": "lentils",
        "category": "protein",
        "unit": "1 lb bag",
        "tags": ["dry", "plant protein"],
        "prices": {
            "Walmart":     1.28,
            "Kroger":      1.49,
            "ALDI":        1.09,
            "Whole Foods": 2.49,
            "Trader Joe's":1.99,
            "Costco":      6.99,
        }
    },
    {
        "name": "chickpeas",
        "category": "protein",
        "unit": "15 oz can",
        "tags": ["canned", "plant protein"],
        "prices": {
            "Walmart":     0.98,
            "Kroger":      1.09,
            "ALDI":        0.79,
            "Whole Foods": 1.69,
            "Trader Joe's":1.19,
            "Costco":      9.49,   # 10 pack
        }
    },
    {
        "name": "tempeh",
        "category": "protein",
        "unit": "8 oz pack",
        "tags": ["plant protein", "fermented"],
        "prices": {
            "Walmart":     2.98,
            "Kroger":      3.49,
            "ALDI":        2.49,
            "Whole Foods": 4.49,
            "Trader Joe's":3.29,
            "Costco":      None,   # not typically stocked
        }
    },
    {
        "name": "kidney beans",
        "category": "protein",
        "unit": "15 oz can",
        "tags": ["canned", "plant protein"],
        "prices": {
            "Walmart":     0.88,
            "Kroger":      0.99,
            "ALDI":        0.69,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      8.99,
        }
    },
    {
        "name": "edamame",
        "category": "protein",
        "unit": "12 oz frozen",
        "tags": ["frozen", "plant protein"],
        "prices": {
            "Walmart":     2.48,
            "Kroger":      2.99,
            "ALDI":        1.99,
            "Whole Foods": 3.99,
            "Trader Joe's":2.49,
            "Costco":      7.99,
        }
    },
    {
        "name": "paneer",
        "category": "protein",
        "unit": "14 oz pack",
        "tags": ["dairy", "plant protein"],
        "prices": {
            "Walmart":     3.98,
            "Kroger":      4.49,
            "ALDI":        None,
            "Whole Foods": 5.99,
            "Trader Joe's":4.99,
            "Costco":      None,
        }
    },

    # ── GRAINS ─────────────────────────────────────
    {
        "name": "rice",
        "category": "grains",
        "unit": "5 lb bag",
        "tags": ["dry", "staple"],
        "prices": {
            "Walmart":     4.48,
            "Kroger":      4.99,
            "ALDI":        3.49,
            "Whole Foods": 6.99,
            "Trader Joe's":4.99,
            "Costco":      12.99,  # 25 lb
        }
    },
    {
        "name": "pasta",
        "category": "grains",
        "unit": "16 oz box",
        "tags": ["dry", "staple"],
        "prices": {
            "Walmart":     1.28,
            "Kroger":      1.49,
            "ALDI":        0.95,
            "Whole Foods": 2.49,
            "Trader Joe's":1.49,
            "Costco":      9.99,   # 6 pack
        }
    },
    {
        "name": "spaghetti",
        "category": "grains",
        "unit": "16 oz box",
        "tags": ["dry", "staple"],
        "prices": {
            "Walmart":     1.28,
            "Kroger":      1.49,
            "ALDI":        0.95,
            "Whole Foods": 2.49,
            "Trader Joe's":1.49,
            "Costco":      9.99,
        }
    },
    {
        "name": "quinoa",
        "category": "grains",
        "unit": "16 oz bag",
        "tags": ["dry", "staple", "protein-rich"],
        "prices": {
            "Walmart":     3.98,
            "Kroger":      4.49,
            "ALDI":        3.19,
            "Whole Foods": 5.99,
            "Trader Joe's":4.49,
            "Costco":      10.99,
        }
    },
    {
        "name": "bread",
        "category": "grains",
        "unit": "20 oz loaf",
        "tags": ["baked"],
        "prices": {
            "Walmart":     1.28,
            "Kroger":      2.49,
            "ALDI":        1.19,
            "Whole Foods": 4.99,
            "Trader Joe's":3.49,
            "Costco":      6.99,   # 2 pack
        }
    },
    {
        "name": "tortilla",
        "category": "grains",
        "unit": "10 count pack",
        "tags": ["baked"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.49,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      7.99,
        }
    },
    {
        "name": "oats",
        "category": "grains",
        "unit": "42 oz canister",
        "tags": ["dry", "breakfast"],
        "prices": {
            "Walmart":     3.48,
            "Kroger":      3.99,
            "ALDI":        2.49,
            "Whole Foods": 5.49,
            "Trader Joe's":3.99,
            "Costco":      8.99,
        }
    },

    # ── DAIRY ──────────────────────────────────────
    {
        "name": "milk",
        "category": "dairy",
        "unit": "1 gallon",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     2.98,
            "Kroger":      3.29,
            "ALDI":        2.49,
            "Whole Foods": 4.99,
            "Trader Joe's":3.49,
            "Costco":      5.99,   # 2 pack
        }
    },
    {
        "name": "greek yogurt",
        "category": "dairy",
        "unit": "32 oz tub",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     4.48,
            "Kroger":      4.99,
            "ALDI":        3.49,
            "Whole Foods": 6.99,
            "Trader Joe's":4.99,
            "Costco":      8.99,
        }
    },
    {
        "name": "mozzarella cheese",
        "category": "dairy",
        "unit": "16 oz bag",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     3.98,
            "Kroger":      4.49,
            "ALDI":        2.99,
            "Whole Foods": 6.49,
            "Trader Joe's":4.49,
            "Costco":      9.99,
        }
    },
    {
        "name": "parmesan cheese",
        "category": "dairy",
        "unit": "8 oz block",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     4.48,
            "Kroger":      5.29,
            "ALDI":        3.99,
            "Whole Foods": 7.99,
            "Trader Joe's":5.49,
            "Costco":      11.99,
        }
    },
    {
        "name": "butter",
        "category": "dairy",
        "unit": "1 lb (4 sticks)",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     3.98,
            "Kroger":      4.49,
            "ALDI":        3.29,
            "Whole Foods": 5.99,
            "Trader Joe's":4.49,
            "Costco":      12.99,  # 4 lb
        }
    },
    {
        "name": "cream cheese",
        "category": "dairy",
        "unit": "8 oz block",
        "tags": ["refrigerated"],
        "prices": {
            "Walmart":     2.48,
            "Kroger":      2.99,
            "ALDI":        1.99,
            "Whole Foods": 4.49,
            "Trader Joe's":2.99,
            "Costco":      7.99,
        }
    },

    # ── PANTRY ─────────────────────────────────────
    {
        "name": "olive oil",
        "category": "pantry",
        "unit": "16.9 oz bottle",
        "tags": ["oil", "staple"],
        "prices": {
            "Walmart":     4.98,
            "Kroger":      5.49,
            "ALDI":        3.99,
            "Whole Foods": 8.99,
            "Trader Joe's":5.99,
            "Costco":      14.99,  # 2 L
        }
    },
    {
        "name": "soy sauce",
        "category": "pantry",
        "unit": "10 oz bottle",
        "tags": ["condiment", "asian"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.49,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      6.99,
        }
    },
    {
        "name": "vegetable broth",
        "category": "pantry",
        "unit": "32 oz carton",
        "tags": ["liquid", "staple"],
        "prices": {
            "Walmart":     1.78,
            "Kroger":      2.09,
            "ALDI":        1.39,
            "Whole Foods": 3.49,
            "Trader Joe's":1.99,
            "Costco":      9.99,   # 6 pack
        }
    },
    {
        "name": "tomato paste",
        "category": "pantry",
        "unit": "6 oz can",
        "tags": ["canned", "staple"],
        "prices": {
            "Walmart":     0.68,
            "Kroger":      0.79,
            "ALDI":        0.55,
            "Whole Foods": 1.29,
            "Trader Joe's":0.99,
            "Costco":      None,
        }
    },
    {
        "name": "coconut milk",
        "category": "pantry",
        "unit": "13.5 oz can",
        "tags": ["canned", "dairy-free"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.59,
            "Whole Foods": 3.29,
            "Trader Joe's":1.99,
            "Costco":      14.99,  # 8 pack
        }
    },
    {
        "name": "canned tomatoes",
        "category": "pantry",
        "unit": "14.5 oz can",
        "tags": ["canned", "staple"],
        "prices": {
            "Walmart":     0.88,
            "Kroger":      0.99,
            "ALDI":        0.69,
            "Whole Foods": 1.79,
            "Trader Joe's":1.19,
            "Costco":      9.99,   # 12 pack
        }
    },
    {
        "name": "peanut butter",
        "category": "pantry",
        "unit": "16 oz jar",
        "tags": ["spread", "protein"],
        "prices": {
            "Walmart":     2.48,
            "Kroger":      2.99,
            "ALDI":        1.99,
            "Whole Foods": 4.99,
            "Trader Joe's":2.99,
            "Costco":      9.99,
        }
    },
    {
        "name": "tahini",
        "category": "pantry",
        "unit": "16 oz jar",
        "tags": ["spread", "middle eastern"],
        "prices": {
            "Walmart":     4.98,
            "Kroger":      5.49,
            "ALDI":        3.99,
            "Whole Foods": 7.99,
            "Trader Joe's":5.99,
            "Costco":      None,
        }
    },

    # ── SPICES ─────────────────────────────────────
    {
        "name": "cumin",
        "category": "spices",
        "unit": "2 oz jar",
        "tags": ["spice", "dried"],
        "prices": {
            "Walmart":     1.48,
            "Kroger":      1.79,
            "ALDI":        1.19,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      5.99,
        }
    },
    {
        "name": "paprika",
        "category": "spices",
        "unit": "2 oz jar",
        "tags": ["spice", "dried"],
        "prices": {
            "Walmart":     1.48,
            "Kroger":      1.79,
            "ALDI":        1.19,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      5.99,
        }
    },
    {
        "name": "turmeric",
        "category": "spices",
        "unit": "2 oz jar",
        "tags": ["spice", "dried"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.49,
            "Whole Foods": 4.49,
            "Trader Joe's":2.99,
            "Costco":      6.99,
        }
    },
    {
        "name": "oregano",
        "category": "spices",
        "unit": "1 oz jar",
        "tags": ["spice", "dried", "italian"],
        "prices": {
            "Walmart":     1.18,
            "Kroger":      1.49,
            "ALDI":        0.99,
            "Whole Foods": 2.99,
            "Trader Joe's":1.99,
            "Costco":      4.99,
        }
    },
    {
        "name": "basil",
        "category": "spices",
        "unit": "0.75 oz jar",
        "tags": ["spice", "dried", "italian"],
        "prices": {
            "Walmart":     1.18,
            "Kroger":      1.49,
            "ALDI":        0.99,
            "Whole Foods": 2.99,
            "Trader Joe's":1.99,
            "Costco":      4.99,
        }
    },
    {
        "name": "chili powder",
        "category": "spices",
        "unit": "2.5 oz jar",
        "tags": ["spice", "dried"],
        "prices": {
            "Walmart":     1.48,
            "Kroger":      1.79,
            "ALDI":        1.19,
            "Whole Foods": 3.49,
            "Trader Joe's":2.49,
            "Costco":      5.99,
        }
    },
    {
        "name": "ginger",
        "category": "spices",
        "unit": "1 fresh root",
        "tags": ["fresh", "asian"],
        "prices": {
            "Walmart":     0.68,
            "Kroger":      0.79,
            "ALDI":        0.59,
            "Whole Foods": 1.29,
            "Trader Joe's":0.99,
            "Costco":      None,
        }
    },

    # ── NUTS & SEEDS ───────────────────────────────
    {
        "name": "walnuts",
        "category": "nuts",
        "unit": "8 oz bag",
        "tags": ["nuts", "healthy fats"],
        "prices": {
            "Walmart":     3.98,
            "Kroger":      4.49,
            "ALDI":        3.29,
            "Whole Foods": 6.99,
            "Trader Joe's":4.99,
            "Costco":      10.99,
        }
    },
    {
        "name": "cashews",
        "category": "nuts",
        "unit": "8 oz bag",
        "tags": ["nuts", "healthy fats"],
        "prices": {
            "Walmart":     4.98,
            "Kroger":      5.49,
            "ALDI":        3.99,
            "Whole Foods": 7.99,
            "Trader Joe's":5.99,
            "Costco":      12.99,
        }
    },
    {
        "name": "almonds",
        "category": "nuts",
        "unit": "8 oz bag",
        "tags": ["nuts", "healthy fats"],
        "prices": {
            "Walmart":     4.48,
            "Kroger":      4.99,
            "ALDI":        3.69,
            "Whole Foods": 7.49,
            "Trader Joe's":5.49,
            "Costco":      11.99,
        }
    },
    {
        "name": "pine nuts",
        "category": "nuts",
        "unit": "2 oz bag",
        "tags": ["nuts", "italian"],
        "prices": {
            "Walmart":     4.98,
            "Kroger":      5.99,
            "ALDI":        None,
            "Whole Foods": 8.99,
            "Trader Joe's":6.49,
            "Costco":      None,
        }
    },

    # ── FRESH HERBS ────────────────────────────────
    {
        "name": "fresh basil",
        "category": "herbs",
        "unit": "0.75 oz pack",
        "tags": ["fresh", "herbs", "italian"],
        "prices": {
            "Walmart":     1.98,
            "Kroger":      2.29,
            "ALDI":        1.49,
            "Whole Foods": 2.99,
            "Trader Joe's":2.49,
            "Costco":      None,
        }
    },
    {
        "name": "cilantro",
        "category": "herbs",
        "unit": "1 bunch",
        "tags": ["fresh", "herbs"],
        "prices": {
            "Walmart":     0.68,
            "Kroger":      0.79,
            "ALDI":        0.59,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      None,
        }
    },
    {
        "name": "parsley",
        "category": "herbs",
        "unit": "1 bunch",
        "tags": ["fresh", "herbs"],
        "prices": {
            "Walmart":     0.68,
            "Kroger":      0.79,
            "ALDI":        0.59,
            "Whole Foods": 1.49,
            "Trader Joe's":0.99,
            "Costco":      None,
        }
    },

    # ── FRUIT ──────────────────────────────────────
    {
        "name": "lemon",
        "category": "fruit",
        "unit": "1 each",
        "tags": ["fresh", "citrus"],
        "prices": {
            "Walmart":     0.48,
            "Kroger":      0.59,
            "ALDI":        0.39,
            "Whole Foods": 0.99,
            "Trader Joe's":0.69,
            "Costco":      4.99,   # 2 lb bag
        }
    },
    {
        "name": "lime",
        "category": "fruit",
        "unit": "1 each",
        "tags": ["fresh", "citrus"],
        "prices": {
            "Walmart":     0.38,
            "Kroger":      0.49,
            "ALDI":        0.29,
            "Whole Foods": 0.79,
            "Trader Joe's":0.59,
            "Costco":      4.49,
        }
    },
    {
        "name": "avocado",
        "category": "fruit",
        "unit": "1 each",
        "tags": ["fresh", "healthy fats"],
        "prices": {
            "Walmart":     0.98,
            "Kroger":      1.29,
            "ALDI":        0.79,
            "Whole Foods": 1.99,
            "Trader Joe's":0.99,
            "Costco":      5.99,   # 5 pack
        }
    },
]


# =====================================================
# STORES COLLECTION
# Real approximate coordinates for US chains
# =====================================================

STORES = [
    {
        "name": "Walmart",
        "type": "supercenter",
        "price_tier": "budget",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 3.9,
        "notes": "Lowest prices, wide availability, bulk options"
    },
    {
        "name": "Kroger",
        "type": "supermarket",
        "price_tier": "mid",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 4.1,
        "notes": "Good produce, frequent sales, loyalty card discounts"
    },
    {
        "name": "ALDI",
        "type": "discount",
        "price_tier": "budget",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 4.3,
        "notes": "Best value per dollar, limited SKUs, store brands only"
    },
    {
        "name": "Whole Foods",
        "type": "premium",
        "price_tier": "premium",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 4.4,
        "notes": "Organic focus, highest quality, highest prices"
    },
    {
        "name": "Trader Joe's",
        "type": "specialty",
        "price_tier": "mid",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 4.5,
        "notes": "Unique products, good value, beloved store brands"
    },
    {
        "name": "Costco",
        "type": "warehouse",
        "price_tier": "bulk",
        "lat": 38.6270,
        "lng": -90.1994,
        "address": "varies by location",
        "rating": 4.6,
        "notes": "Bulk only, membership required, best per-unit price"
    },
]


# =====================================================
# DEMO USER
# =====================================================

DEMO_USER = {
    "email": "demo@smartcart.ai",
    "name": "Demo User",
    "created_at": datetime.now(timezone.utc),
    "preferences": {
        "dietary": ["vegetarian"],
        "budget_weekly": 100,
        "servings": 2,
        "cuisine_preferences": ["italian", "asian", "mexican"],
        "disliked_ingredients": [],
        "favorite_stores": ["ALDI", "Trader Joe's"],
        "pantry": ["salt", "pepper", "olive oil", "garlic"],
    },
    "location": {
        "lat":     38.6270,
        "lng":    -90.1994,
        "city":    "Saint Louis",
        "region":  "Missouri",
        "country": "US",
    }
}


# =====================================================
# SAMPLE MEAL PLANS
# =====================================================

SAMPLE_MEAL_PLANS = [
    {
        "user_email": "demo@smartcart.ai",
        "week_of": datetime(2025, 5, 26, tzinfo=timezone.utc),
        "meals": {
            "Monday":    "Tomato Veg Pasta",
            "Tuesday":   "Tofu Stir Fry",
            "Wednesday": "Lentil Curry",
            "Thursday":  "Veggie Tacos",
            "Friday":    "Mushroom Risotto",
        },
        "shopping_list": [
            "tomatoes", "pasta", "garlic", "olive oil", "basil",
            "tofu", "broccoli", "soy sauce", "ginger", "rice",
            "lentils", "coconut milk", "cumin", "turmeric", "onions",
            "tortilla", "black beans", "bell pepper", "chili powder",
            "mushrooms", "vegetable broth", "parmesan cheese",
        ],
        "total_cost":   67.40,
        "money_saved":  14.20,
        "store_used":   "ALDI",
        "created_at":   datetime.now(timezone.utc),
    },
    {
        "user_email": "demo@smartcart.ai",
        "week_of": datetime(2025, 6, 2, tzinfo=timezone.utc),
        "meals": {
            "Monday":    "Greek Salad Bowl",
            "Tuesday":   "Black Bean Tacos",
            "Wednesday": "Veggie Fried Rice",
            "Thursday":  "Chickpea Curry",
            "Friday":    "Zucchini Pasta",
        },
        "shopping_list": [
            "cucumber", "tomatoes", "parmesan cheese", "olive oil", "lemon",
            "black beans", "tortilla", "avocado", "cilantro", "lime",
            "rice", "soy sauce", "carrot", "onions", "garlic",
            "chickpeas", "coconut milk", "turmeric", "ginger", "spinach",
            "zucchini", "pasta", "basil",
        ],
        "total_cost":   71.80,
        "money_saved":  18.60,
        "store_used":   "Trader Joe's",
        "created_at":   datetime.now(timezone.utc),
    },
]


# =====================================================
# SEED RUNNER
# =====================================================

def seed_all():
    db = get_db()

    # ── PRODUCTS ──────────────────────────────────
    print("\n📦 Seeding products collection...")
    col = db["products"]
    col.drop()   # fresh start

    # Add metadata fields to every product
    now = datetime.now(timezone.utc)
    for p in PRODUCTS:
        p["created_at"]   = now
        p["updated_at"]   = now
        p["available_at"] = [
            store for store, price in p["prices"].items()
            if price is not None
        ]

    result = col.insert_many(PRODUCTS)
    print(f"   ✅ Inserted {len(result.inserted_ids)} products")

    # Index for fast name + category lookups
    col.create_index("name")
    col.create_index("category")
    col.create_index("tags")
    print("   ✅ Created indexes on name, category, tags")

    # ── STORES ────────────────────────────────────
    print("\n🏪 Seeding stores collection...")
    col = db["stores"]
    col.drop()

    for s in STORES:
        s["created_at"] = now

    result = col.insert_many(STORES)
    print(f"   ✅ Inserted {len(result.inserted_ids)} stores")

    # ── USERS ─────────────────────────────────────
    print("\n👤 Seeding users collection...")
    col = db["users"]
    col.drop()

    col.insert_one(DEMO_USER)
    col.create_index("email", unique=True)
    print("   ✅ Inserted demo user (demo@smartcart.ai)")
    print("   ✅ Created unique index on email")

    # ── MEAL PLANS ────────────────────────────────
    print("\n🗓️  Seeding meal_plans collection...")
    col = db["meal_plans"]
    col.drop()

    result = col.insert_many(SAMPLE_MEAL_PLANS)
    col.create_index("user_email")
    col.create_index("week_of")
    print(f"   ✅ Inserted {len(result.inserted_ids)} sample meal plans")
    print("   ✅ Created indexes on user_email, week_of")

    # ── SUMMARY ───────────────────────────────────
    print(f"""
╔══════════════════════════════════════╗
║   SmartCart MongoDB Seed Complete!   ║
╠══════════════════════════════════════╣
║  Database  : {DB_NAME:<23} ║
║  Products  : {len(PRODUCTS)} items, 6 stores each  ║
║  Stores    : {len(STORES)} chains seeded          ║
║  Users     : 1 demo user             ║
║  Meal Plans: {len(SAMPLE_MEAL_PLANS)} sample weeks          ║
╚══════════════════════════════════════╝

Next step: rewrite price_engine.py to query MongoDB
    """)


if __name__ == "__main__":
    seed_all()