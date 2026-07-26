def clean_shopping_list(items):
    if not items:
        return []

    cleaned = set()

    for i in items:
        if not i:
            continue
        cleaned.add(str(i).strip().lower())

    return list(cleaned)


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