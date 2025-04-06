import requests
import time


def get_coordinates(address):
    """Get coordinates (latitude, longitude) for an address using Nominatim."""
    headers = {"User-Agent": "PythonGeocoder/1.0"}  # Generic user agent

    # Add a delay to respect usage policy
    time.sleep(1)

    response = requests.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": address, "format": "json"},
        headers=headers,
    )

    # Check if response was successful
    if response.status_code != 200:
        print(f"Error: API returned status code {response.status_code}")
        print(f"Response content: {response.text}")
        raise Exception(
            f"Nominatim API request failed with status {response.status_code}"
        )

    # Try to parse JSON and handle empty results
    data = response.json()
    if not data:
        raise Exception(f"No coordinates found for address: {address}")

    lat = data[0]["lat"]
    lon = data[0]["lon"]
    return float(lat), float(lon)


def get_distance_osrm(coord_from, coord_to):
    """Calculate distance between two coordinates using OSRM API."""
    # Format coordinates as 'lon,lat' (note the order)
    from_point = f"{coord_from[1]},{coord_from[0]}"
    to_point = f"{coord_to[1]},{coord_to[0]}"

    url = f"http://router.project-osrm.org/route/v1/driving/{from_point};{to_point}"
    params = {
        "overview": "false",
        "alternatives": "false",
    }

    headers = {"User-Agent": "PythonGeocoder/1.0"}

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise exception for HTTP errors

        data = response.json()

        if data["code"] != "Ok":
            raise Exception(f"OSRM API error: {data['code']}")

        # Distance in meters
        distance_meters = data["routes"][0]["distance"]
        # Convert to kilometers
        distance_km = distance_meters / 1000

        return distance_km

    except requests.exceptions.RequestException as e:
        print(f"Error making request to OSRM API: {e}")
        raise
    except (KeyError, IndexError) as e:
        print(f"Error parsing OSRM API response: {e}")
        print(f"Response content: {response.text}")
        raise
