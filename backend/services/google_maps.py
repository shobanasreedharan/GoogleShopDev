import requests
import polyline
import os
from dotenv import load_dotenv

load_dotenv()

GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")


def get_google_route(origin, destinations):

    if not destinations:
        return []

    origin_lat, origin_lng = map(float, origin)

    cleaned = [(float(lat), float(lng)) for lat, lng in destinations]

    destination_lat, destination_lng = cleaned[-1]

    waypoints = cleaned[:-1]

    url = "https://maps.googleapis.com/maps/api/directions/json"

    params = {
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{destination_lat},{destination_lng}",
        "mode": "driving",
        "key": GOOGLE_MAPS_API_KEY
    }

    # ADD WAYPOINTS ONLY IF THEY EXIST
    if waypoints:
        params["waypoints"] = "|".join(
            [f"{lat},{lng}" for lat, lng in waypoints]
        )

    response = requests.get(url, params=params).json()

    if response.get("status") != "OK":
        print("Google API error:", response)
        return []

    polyline_str = response["routes"][0]["overview_polyline"]["points"]

    return polyline.decode(polyline_str)