import httpx
from typing import Optional

STEAM_INVENTORY_URL = "https://steamcommunity.com/inventory/{steam_id}/730/2"
PAGE_SIZE = 75  # Steam's maximum per-page limit


async def get_inventory(steam_id: str) -> list[dict]:
    url = STEAM_INVENTORY_URL.format(steam_id=steam_id)
    all_assets: list[dict] = []
    all_descriptions: dict[tuple, dict] = {}
    start_assetid: Optional[str] = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        while True:
            params: dict = {"l": "english", "count": PAGE_SIZE}
            if start_assetid:
                params["start_assetid"] = start_assetid

            resp = await client.get(url, params=params)
            if resp.status_code == 429:
                raise IOError("Steam rate limit reached. Please wait a few minutes and try again.")
            resp.raise_for_status()
            data = resp.json()

            if not data or not data.get("success"):
                raise ValueError("Failed to fetch inventory — make sure it is set to public.")

            all_assets.extend(data.get("assets", []))

            for d in data.get("descriptions", []):
                key = (d["classid"], d["instanceid"])
                all_descriptions[key] = d

            if data.get("more_items"):
                start_assetid = data.get("last_assetid")
            else:
                break

    items: list[dict] = []
    seen: dict[str, dict] = {}

    for asset in all_assets:
        key = (asset["classid"], asset["instanceid"])
        desc = all_descriptions.get(key, {})
        if desc.get("tradable") == 0:
            continue
        name = desc.get("market_hash_name")
        if not name:
            continue
        if name in seen:
            seen[name]["quantity"] += 1
        else:
            item = {
                "market_hash_name": name,
                "name": desc.get("name", name),
                "icon_url": f"https://community.fastly.steamstatic.com/economy/image/{desc.get('icon_url', '')}",
                "exterior": _get_tag(desc, "Exterior"),
                "rarity": _get_tag(desc, "Rarity"),
                "type": _get_tag(desc, "Type"),
                "quantity": 1,
            }
            items.append(item)
            seen[name] = item

    return items


def _get_tag(desc: dict, category: str) -> Optional[str]:
    for tag in desc.get("tags", []):
        if tag.get("category") == category:
            return tag.get("localized_tag_name")
    return None
