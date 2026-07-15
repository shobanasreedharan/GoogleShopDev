import streamlit as st
import requests
import pydeck as pdk
import pandas as pd
import numpy as np

try:
    from backend.services.google_maps import get_google_route
except:
    get_google_route = None

if "data" not in st.session_state:
    st.session_state.data = None

if "selected_subs" not in st.session_state:
    st.session_state.selected_subs = {}

# =====================================================
# CONFIG
# =====================================================
st.set_page_config(page_title="Smart Grocery AI", layout="wide")

API_URL = "http://127.0.0.1:8000/generate"

st.title("🛒 Smart Grocery AI")

# =====================================================
# MODE
# =====================================================
st.subheader("🍽️ Meal Planning Mode")

mode = st.radio(
    "Choose Plan Type",
    ["🍽️ Single Meal", "📅 Weekly Meals", "🛍️ Shopping List Only", "🍽️ + 🛍️ Meal & Shopping List"],
    horizontal=True
)

weekly_meals = {}
manual_items = []
selected_substitutions = {}

# =====================================================
# MEAL INPUTS
# =====================================================

if mode == "🍽️ Single Meal":

    dish = st.text_input("Enter one meal")

    if dish:
        weekly_meals = {"single_meal": dish}


elif mode == "📅 Weekly Meals":

    st.write("Enter your weekly meals (Mon–Sun)")

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    for day in days:
        meal = st.text_input(f"{day} meal", key=day)
        if meal:
            weekly_meals[day] = meal


elif mode == "🛍️ Shopping Only":

    manual_text = st.text_area("Items (comma separated)")
    manual_items = [x.strip().lower() for x in manual_text.split(",") if x.strip()]


else:  # Mixed

    col1, col2 = st.columns(2)

    with col1:
        dish = st.text_input("Enter meal")
        if dish:
            weekly_meals = {"single_meal": dish}

    with col2:
        manual_text = st.text_area("Extra items (comma separated)")
        manual_items = [x.strip().lower() for x in manual_text.split(",") if x.strip()]

# =====================================================
# PANTRY INPUT (RESTORED)
# =====================================================
st.markdown("---")
st.subheader("🥫 Pantry Items")

pantry_text = st.text_area(
    "Items you already have (comma separated)",
    placeholder="salt, oil, garlic"
)

pantry_items = [x.strip().lower() for x in pantry_text.split(",") if x.strip()]

# =====================================================
# DIETARY PREFERENCE
# =====================================================
st.subheader("🥗 Dietary Preference")

dietary = st.selectbox(
    "Choose diet type",
    ["None", "Vegetarian", "Vegan", "Keto", "High Protein", "Low Carb"]
)

# =====================================================
# BUTTON
# =====================================================
if st.button("✨ Generate Smart Plan"):
    st.session_state.data = None
    data = st.session_state.data
    payload = {
        "weekly_meals": weekly_meals,
        "manual_items": manual_items,
        "budget": 100,
        "pantry_items": pantry_items,
        "dietary_instruction": dietary,
        "selected_substitutions": selected_substitutions,
        "mode": mode
    }

    with st.spinner("Generating AI plan..."):
        res = requests.post(API_URL, json=payload)

    if res.status_code != 200:
        st.error(res.text)
        st.stop()

    st.session_state.data = res.json()
    data = st.session_state.data

    shopping_list = data.get("shopping_list", [])
    stores = data.get("recommended_stores", [])
    route = data.get("optimized_route", [])
    location = data.get("user_location", {})
    subs = data.get("substitutions", {})
    winner_stores = stores[:3]

    # =====================================================
    # SHOPPING LIST
    # =====================================================
    st.header("🛍️ Shopping List")

    for item in shopping_list:
        st.write("✅", item)

    # =====================================================
    # NUTRITION (FIXED STRUCTURE)
    # =====================================================
    st.header("🥗 Nutrition Report in grams")

    nutrition_report = data.get("nutrition_report") or {}

    # IMPORTANT: correct key from backend
    nutrition_scores = nutrition_report.get("nutrition_scores") or {}
    ai_feedback = nutrition_report.get("ai_feedback") or {}

    #st.write("nutrition_scores:", nutrition_scores)
    #st.write("ai_feedback:", ai_feedback)

    col1, col2, col3, col4 = st.columns(4)

    col1.metric("Protein", f"{nutrition_scores.get('protein_g',0)}")
    col2.metric("Carbs", f"{nutrition_scores.get('carbs_g', 0)}")
    col3.metric("Fat", f"{nutrition_scores.get('fat_g',0)}")
    col4.metric("Fiber", f"{nutrition_scores.get('fiber_g', 0)}")

    #st.write("RAW NUTRITION:", data.get("nutrition_report"))

    st.metric("Fat", f"{nutrition_scores.get('fat_score', 0)}/10")

    if ai_feedback.get("summary"):
        st.info(ai_feedback["summary"])

    if ai_feedback.get("recommendations"):
        st.markdown("**Recommendations:**")
        for r in ai_feedback["recommendations"]:
            st.write("👉", r)

    # =====================================================
    # SUBSTITUTIONS
    # =====================================================
    st.header("🔄 Substitutions")

    subs = data.get("substitutions", {})

    selected_subs = {}

    for item, options in subs.items():
        current = st.session_state.selected_subs.get(
            item,
            "Keep original"
        )

        choice = st.radio(
            f"Choose replacement for {item}",
            options=["Keep original"] + options,
            index=(["Keep original"] + options).index(current)
            if current in ["Keep original"] + options
            else 0,
            key=f"sub_{item}"
        )

        st.session_state.selected_subs[item] = choice

    # =====================================================
    # STORE PRICE COMPARISON TABLE
    # =====================================================

    st.header("🏪 Store Price Comparison")

    if not stores:
        st.warning("No stores found")
    else:

        # ---------------------------------
        # Build price matrix
        # ---------------------------------

        all_items = set()

        for store in stores:
            for item in store.get("items", []):
                all_items.add(item.get("item"))

        all_items = sorted(list(all_items))

        comparison = pd.DataFrame(index=all_items)

        basket_totals = {}

        for store in stores:

            store_name = store.get("store_name")

            prices = {}

            total = 0

            for item in store.get("items", []):
                item_name = item.get("item")
                price = float(item.get("price", 0))

                prices[item_name] = price
                total += price

            basket_totals[store_name] = round(total, 2)

            comparison[store_name] = [
                prices.get(item, np.nan)
                for item in comparison.index
            ]

        # ---------------------------------
        # Add basket total row
        # ---------------------------------

        comparison.loc["🛒 TOTAL BASKET"] = [
            basket_totals.get(col, 0)
            for col in comparison.columns
        ]


        # ---------------------------------
        # Highlight cheapest value per row
        # ---------------------------------

        def highlight_cheapest(row):

            styles = [""] * len(row)

            values = pd.to_numeric(row, errors="coerce")

            if values.notna().any():
                min_val = values.min()

                styles = [
                    (
                        "background-color:#90EE90;"
                        "font-weight:bold;"
                    )
                    if pd.notna(v) and v == min_val
                    else ""
                    for v in values
                ]

            return styles


        styled = (
            comparison
            .style
            .format("${:.2f}", na_rep="—")
            .apply(highlight_cheapest, axis=1)
        )

        st.dataframe(
            styled,
            use_container_width=True,
            height=600
        )

        # ---------------------------------
        # CHEAPEST ITEM ANALYSIS
        # ---------------------------------

        winner_counts = {}
        winner_totals = {}

        for item_name in comparison.index:

            if item_name == "🛒 TOTAL BASKET":
                continue

            row = pd.to_numeric(
                comparison.loc[item_name],
                errors="coerce"
            )

            if not row.notna().any():
                continue

            cheapest_price = row.min()

            winning_store = row.idxmin()

            winner_counts[winning_store] = (
                    winner_counts.get(winning_store, 0) + 1
            )

            winner_totals[winning_store] = (
                    winner_totals.get(winning_store, 0)
                    + cheapest_price
            )

        # =====================================
        # OVERALL CHEAPEST BASKET
        # =====================================

        overall_cheapest = round(
            sum(winner_totals.values()),
            2
        )

        st.success(
            f"🏆 Cheapest Possible Basket Across All Stores = "
            f"${overall_cheapest:.2f}"
        )

        # =====================================
        # CONTRIBUTION BREAKDOWN
        # =====================================

        st.markdown("### 🏆 Cheapest Item Winners")

        winner_df = pd.DataFrame({
            "Store": list(winner_counts.keys()),
            "Items Won": [
                winner_counts[s]
                for s in winner_counts.keys()
            ],
            "Contribution ($)": [
                round(winner_totals[s], 2)
                for s in winner_counts.keys()
            ]
        })

        winner_df = winner_df.sort_values(
            "Contribution ($)",
            ascending=False
        )

        st.dataframe(
            winner_df,
            use_container_width=True,
            hide_index=True
        )

    # =====================================================
    # OPTIMIZED SHOPPING ROUTE
    # =====================================================

    st.header("🚗 Optimized Shopping Route")

    if not winner_stores:
        st.warning("No optimized stores found")
    else:
        for idx, store in enumerate(winner_stores, start=1):
            st.write(
                f"{idx}. {store['store_name']} "
                f"({store.get('distance_km', 0):.1f} km)"
            )

    # =====================================================
    # MAP (FULL FIX)
    # =====================================================
    st.header("🗺️ Route Map")

    if not location or not location.get("lat") or not location.get("lng"):
        st.warning("📍 Location not available — map disabled")
        st.stop()

    origin = (float(location["lat"]), float(location["lng"]))

    store_points = []
    for s in  winner_stores:
        if s.get("lat") and s.get("lng"):
            store_points.append({
                "name": s.get("store_name"),
                "lat": float(s["lat"]),
                "lng": float(s["lng"]),
                "color": [255, 140, 0]
            })

    # route fallback
    route_coords = []

    try:
        if get_google_route and store_points:
            destinations = [
                (
                    float(s["lat"]),
                    float(s["lng"])
                )
                for s in winner_stores if s.get("lat") and s.get("lng")
            ]
            raw_route = get_google_route(origin, destinations)

            if raw_route:
                route_coords = [[lng, lat] for lat, lng in raw_route]
    except:
        pass

    if not route_coords:
        route_coords = [[location["lng"], location["lat"]]]
        route_coords += [[p["lng"], p["lat"]] for p in store_points]

    points = [
        {"name": "You", "lat": origin[0], "lng": origin[1], "color": [0, 200, 0]}
    ] + store_points

    layer_points = pdk.Layer(
        "ScatterplotLayer",
        data=points,
        get_position="[lng, lat]",
        get_radius=120,
        get_color="color",
        pickable=True
    )

    layer_route = pdk.Layer(
        "PathLayer",
        data=[{"path": route_coords}],
        get_path="path",
        get_width=5,
        width_min_pixels=2,
        get_color=[0, 120, 255]
    )

    view_state = pdk.ViewState(
        latitude=origin[0],
        longitude=origin[1],
        zoom=11,
        pitch=40
    )

    st.pydeck_chart(
        pdk.Deck(
            layers=[layer_points, layer_route],
            initial_view_state=view_state,
            tooltip={"text": "{name}"}
        )
    )