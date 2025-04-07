import requests
import time
import random
import re
import logging
import json
from math import radians, cos, sin, asin, sqrt
from requests.exceptions import RequestException, ConnectionError, Timeout

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def haversine_distance(coord1, coord2):
    """Calculate the great circle distance ('as the crow flies') between two coordinates in km"""
    lat1, lon1 = coord1
    lat2, lon2 = coord2
    
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r

def get_coordinates(address, max_retries=5, initial_backoff=1, max_backoff=60, timeout=10):
    """
    Get coordinates with comprehensive error handling for network issues and complex addresses.
    """
    headers = {"User-Agent": "PythonGeocoder/1.0"}
    
    # Remove "вл" abbreviation if present in the address
    address = re.sub(r'(?<=\s)вл(\d)', r'\1', address)
    
    # Create address variations from most specific to most general
    address_variations = [
        address,
        # Keep only the numeric part of building numbers
        re.sub(r'(\d+)[А-Яа-я]+\d*', r'\1', address),
        # Simple street + main building number pattern
        re.sub(r'(улица\s+[А-Яа-я]+|[А-Яа-я]+\s+переулок),\s+\d+[А-Яа-я]*.*', r'\1', address)
    ]
    
    last_exception = None
    
    # Try each address variant
    for addr_variant in address_variations:
        # Reset backoff for each new address variant
        backoff = initial_backoff
        
        # Retry loop with exponential backoff
        for attempt in range(max_retries):
            try:
                # Add timeout to prevent hanging requests
                params = {
                    "q": addr_variant,
                    "format": "json",
                    "countrycodes": "ru",
                    "addressdetails": 1
                }
                
                # Sleep before making request (respect usage policy + backoff)
                actual_sleep = backoff + random.uniform(0, 0.5)  # Add jitter
                time.sleep(actual_sleep)
                
                response = requests.get(
                    "https://nominatim.openstreetmap.org/search",
                    params=params,
                    headers=headers,
                    timeout=timeout
                )
                
                response.raise_for_status()
                data = response.json()
                
                if data:
                    lat = data[0]["lat"]
                    lon = data[0]["lon"]
                    if addr_variant != address:
                        logger.info(f"Found coordinates using simplified address: '{addr_variant}' for '{address}'")
                    return float(lat), float(lon)
                
                # If we got a 200 response but no data, this variant might not work
                backoff = min(backoff * 2, max_backoff)
                
            except (ConnectionError, Timeout, ConnectionResetError, BrokenPipeError) as e:
                # Network-related errors that merit retrying
                last_exception = e
                backoff = min(backoff * 2, max_backoff)
                
                logger.warning(f"Network error for '{addr_variant}' on attempt {attempt+1}/{max_retries}. "
                      f"Retrying in {backoff:.2f}s: {str(e)}")
                
                time.sleep(backoff)
                continue
                
            except RequestException as e:
                # Other request errors
                last_exception = e
                
                # Only retry for 5xx server errors
                if hasattr(e, 'response') and e.response and 500 <= e.response.status_code < 600:
                    backoff = min(backoff * 2, max_backoff)
                    logger.warning(f"Server error {e.response.status_code} for '{addr_variant}' on attempt {attempt+1}/{max_retries}. "
                          f"Retrying in {backoff:.2f}s")
                    time.sleep(backoff)
                else:
                    # Client errors (4xx) - try next address variant
                    logger.error(f"Client error for '{addr_variant}': {e}")
                    break  # Skip to next address variant
                    
            except Exception as e:
                # Unexpected errors
                last_exception = e
                logger.error(f"Unexpected error for '{addr_variant}': {e}")
                break  # Skip to next address variant
    
    # Special fallback: just try the street name
    try:
        # Extract just street name as last resort
        street_match = re.search(r'(?:Москва|Moscow),?\s+(?:улица|ул\.|переулок)\s+([А-Яа-я\w\s]+)', address)
        if street_match:
            fallback = f"Москва, {street_match.group(1)}"
            
            time.sleep(2)  # Longer delay for last attempt
            response = requests.get(
                "https://nominatim.openstreetmap.org/search",
                params={"q": fallback, "format": "json", "countrycodes": "ru"},
                headers=headers,
                timeout=15  # Longer timeout for final attempt
            )
            
            if response.status_code == 200:
                data = response.json()
                if data:
                    lat = data[0]["lat"]
                    lon = data[0]["lon"]
                    logger.warning(f"Using street-level coordinates for: {address}")
                    return float(lat), float(lon)
    except Exception as e:
        logger.error(f"Fallback geocoding failed: {e}")
    
    # If we've exhausted all variants and retries
    error_msg = f"No coordinates found for address after multiple attempts: {address}. Last error: {last_exception}"
    raise Exception(error_msg)

def get_distance_osrm(coord_from, coord_to, max_retries=5, initial_backoff=1, max_backoff=60, timeout=10):
    """
    Calculate walking distance between two coordinates using only OpenStreetMap's routing API.
    Uses haversine distance for comparison only.
    """
    # Format coordinates as 'lon,lat' (note the order)
    from_point = f"{coord_from[1]},{coord_from[0]}"
    to_point = f"{coord_to[1]},{coord_to[0]}"
    
    # Only use OpenStreetMap endpoint for foot routing
    endpoint_url = f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{from_point};{to_point}"
    
    params = {
        "overview": "false",
        "alternatives": "false",
    }
    
    headers = {"User-Agent": "PythonGeocoder/1.0"}
    
    # Retry loop with exponential backoff
    backoff = initial_backoff
    
    for attempt in range(max_retries):
        try:
            # Add timeout parameter to prevent hanging requests
            response = requests.get(endpoint_url, params=params, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Check if we have valid route data
            if "routes" in data and len(data["routes"]) > 0:
                if "distance" in data["routes"][0]:
                    # Extract distance in meters and convert to kilometers
                    distance_meters = data["routes"][0]["distance"]
                    distance_km = distance_meters / 1000
                    
                    # Calculate straight-line distance for internal comparison only
                    straight_line = haversine_distance(coord_from, coord_to)
                    ratio = distance_km / straight_line if straight_line > 0 else 0
                    
                    # Only log at debug level to avoid duplication
                    if ratio > 3:
                        logger.warning(f"Walking distance is {ratio:.1f}x the straight-line distance. This might be unrealistic.")
                    
                    # Return only the OpenStreetMap result
                    return distance_km
            else:
                raise Exception(f"Unexpected API response format: {json.dumps(data)[:100]}...")
            
        except (ConnectionError, Timeout, ConnectionResetError, BrokenPipeError) as e:
            # Network-related errors that merit retrying
            wait_time = backoff + random.uniform(0, 1)
            
            logger.warning(f"Network error on attempt {attempt+1}/{max_retries}. "
                  f"Retrying in {wait_time:.2f}s: {str(e)}")
            time.sleep(wait_time)
            
            # Exponential backoff
            backoff = min(backoff * 2, max_backoff)
            
        except Exception as e:
            # Other errors - log and retry until max attempts
            logger.error(f"Error with OpenStreetMap routing: {e}")
            
            if attempt < max_retries - 1:
                wait_time = backoff + random.uniform(0, 1)
                logger.info(f"Retrying in {wait_time:.2f}s...")
                time.sleep(wait_time)
                backoff = min(backoff * 2, max_backoff)
            else:
                # If we've exhausted all retries, use fallback
                break
    
    # If all attempts failed, calculate and return the straight-line distance with a walking factor
    straight_line = haversine_distance(coord_from, coord_to)
    estimated_walking = straight_line * 1.4  # Apply typical walking winding factor
    logger.warning(f"All routing API attempts failed. Using estimated walking distance: {estimated_walking:.2f}km (straight-line * 1.4)")
    return estimated_walking

def calculate_distance(from_point=None, from_address=None, to_point=None, to_address=None):
    """
    Flexible function to calculate distance between two points, allowing either coordinates or addresses for both points.
    
    Parameters:
    from_point (tuple): Starting point coordinates as (lat, lon) tuple, optional if from_address is provided
    from_address (str): Starting point address, optional if from_point is provided
    to_point (tuple): Ending point coordinates as (lat, lon) tuple, optional if to_address is provided
    to_address (str): Ending point address, optional if to_point is provided
    
    Returns:
    float: Distance in kilometers
    """
    try:
        # Get coordinates for the starting point
        if from_point is not None:
            coord1 = from_point
            logger.info(f"Using provided coordinates for starting point: {coord1}")
        elif from_address is not None:
            logger.info(f"Getting coordinates for: {from_address}")
            coord1 = get_coordinates(from_address)
            logger.info(f"Coordinates for {from_address}: {coord1}")
        else:
            raise ValueError("Either from_point or from_address must be provided")
        
        # Get coordinates for the ending point
        if to_point is not None:
            coord2 = to_point
            logger.info(f"Using provided coordinates for ending point: {coord2}")
        elif to_address is not None:
            logger.info(f"Getting coordinates for: {to_address}")
            coord2 = get_coordinates(to_address)
            logger.info(f"Coordinates for {to_address}: {coord2}")
        else:
            raise ValueError("Either to_point or to_address must be provided")
        
        # Calculate straight-line distance for comparison only
        straight_line = haversine_distance(coord1, coord2)
        logger.info(f"Straight-line distance (for comparison): {straight_line:.2f}km")
        
        # Calculate walking distance using OpenStreetMap
        try:
            walking_distance = get_distance_osrm(coord1, coord2)
            # Only log the final result once
            logger.info(f"OpenStreetMap walking distance: {walking_distance:.2f}km")
            
            # Log the ratio for informational purposes
            ratio = walking_distance / straight_line if straight_line > 0 else 0
            logger.info(f"Walking/Straight-line ratio: {ratio:.2f}")
            
            return walking_distance
            
        except Exception as e:
            logger.error(f"OpenStreetMap routing failed: {e}")
            
            # Fall back to straight-line with typical winding factor
            estimated_distance = straight_line * 1.4
            logger.warning(f"Using estimated walking distance: {estimated_distance:.2f}km (straight-line * 1.4)")
            return estimated_distance
            
    except Exception as e:
        logger.error(f"Error calculating distance: {e}")
        return None

def calculate_distance_between_addresses(addr1, addr2):
    """
    Calculate the walking distance between two addresses using OpenStreetMap's routing API.
    This is a convenience wrapper around the more flexible calculate_distance function.
    """
    return calculate_distance(from_address=addr1, to_address=addr2)

if __name__ == "__main__":
    # Define test addresses
    test_addresses = [
        # Pairs of addresses to test
        ("Москва, Большой Саввинский переулок, 3", "Москва, Новодевичий проезд, 8"),
        ("Москва, Большой Саввинский переулок, 3", "Москва, Новодевичий проезд, 4"),
        ("Москва, Большой Саввинский переулок, 3", "Москва, Большой Саввинский переулок, 19")
        # Add more test pairs as needed
    ]
    
    # Define mixed test cases with coordinates and addresses
    test_mixed_cases = [
        ("55.7355742, 37.5701095960607", "Москва, Кутузовский проспект, вл2/1"),
        ("55.7355742, 37.5701095960607", "Москва, Хлебный переулок, 10"),
        ("55.7355742, 37.5701095960607", "Москва, улица Волхонка, 5/6С9")
    ]
    
    # Test each pair of addresses
    results = []
    
    logger.info("=" * 80)
    logger.info("TESTING WALKING DISTANCE CALCULATION METHODS")
    logger.info("=" * 80)
    
    # Test regular address pairs
    for addr1, addr2 in test_addresses:
        logger.info("-" * 80)
        logger.info(f"Testing walking distance between '{addr1}' and '{addr2}'")
        
        # Calculate walking distance using our main function - it already logs what we need
        walking_distance = calculate_distance_between_addresses(addr1, addr2)
        
        if walking_distance is not None:
            results.append((addr1, addr2, walking_distance))
    
    # Test mixed cases (coordinates + address)
    logger.info("=" * 80)
    logger.info("TESTING MIXED CASES (COORDINATES + ADDRESS)")
    logger.info("=" * 80)
    
    for coord_str, address in test_mixed_cases:
        logger.info("-" * 80)
        logger.info(f"Testing walking distance between coordinates '{coord_str}' and address '{address}'")
        
        # Parse the coordinate string
        try:
            lat, lon = map(float, coord_str.split(','))
            from_point = (lat, lon)
            
            # Calculate using our flexible function
            walking_distance = calculate_distance(from_point=from_point, to_address=address)
            
            if walking_distance is not None:
                results.append((f"Coordinates ({lat}, {lon})", address, walking_distance))
        except Exception as e:
            logger.error(f"Error processing coordinate string '{coord_str}': {e}")
    
    # Print summary
    logger.info("=" * 80)
    logger.info("SUMMARY OF WALKING DISTANCES")
    logger.info("=" * 80)
    
    for point1, point2, distance in results:
        logger.info(f"Walking distance from '{point1}' to '{point2}': {distance:.2f} km")