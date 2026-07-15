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

        if not store.get("lat") or not store.get("lng"):
            continue

        valid.append(r)

    return valid