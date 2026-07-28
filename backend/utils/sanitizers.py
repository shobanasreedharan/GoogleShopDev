import re


_NON_INGREDIENT_DISHES = {"sambar", "coconut chutney", "chutney"}
_INGREDIENT_PREFIX_RE = re.compile(r"^(?:\d+(?:[./]\d+)?|one|two|three|four|five|six|seven|eight|nine|ten)\s+(?:cups?|tbsp|tablespoons?|tsp|teaspoons?|grams?|g|kg|lbs?|pounds?|oz|ounces?|small|medium|large|big)\s+", re.IGNORECASE)


def clean_ingredient_name(item: str) -> str:
    value = str(item or "").lower().strip()
    if not value:
        return ""
    value = re.sub(r"\([^)]*\)", "", value)
    value = re.sub(r"\b(for garnish|to taste|as needed|optional|finely chopped|chopped|diced|sliced|minced)\b", "", value)
    value = re.sub(r"^[\d./]+\s*", "", value)
    value = re.sub(r"^(?:cups?|tbsp|tablespoons?|tsp|teaspoons?|grams?|g|kg|lbs?|pounds?|oz|ounces?)\s+", "", value)
    while True:
        updated = _INGREDIENT_PREFIX_RE.sub("", value).strip()
        if updated == value:
            break
        value = updated
    value = re.sub(r"\b(small|medium|large|big|fresh|dried)\b", "", value)
    value = re.sub(r"\s+", " ", value).strip(" ,.-")
    if value in _NON_INGREDIENT_DISHES:
        return ""
    return value


def clean_shopping_list(items):
    if not items:
        return []

    cleaned = []
    seen = set()

    for i in items:
        value = clean_ingredient_name(i)
        if value and value not in seen:
            cleaned.append(value)
            seen.add(value)

    return cleaned


def clean_stores(results):
    if not results:
        return []

    valid = []

    for r in results:
        store = r.get("store")
        if not store:
            continue

        has_coordinates = store.get("lat") is not None and store.get("lng") is not None
        has_prices = bool(r.get("items") or r.get("price_breakdown"))
        if not has_coordinates and not has_prices:
            continue

        valid.append(r)

    return valid