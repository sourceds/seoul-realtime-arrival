"""
Seoul Metropolitan Subway Real-Time Arrival Checker
Fetches live arrival info from Seoul Open API for bus lines.

Environment variables required:
    BUS_KEY - Seoul Bus Open API key
"""

import requests
import json
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUS_BASE_URL = "http://ws.bus.go.kr/api/rest/arrive"

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class BusInfo:
    #Holds the arrival messages for a single bus/train.
    
    destination: str # ?
    current_station: str # 'stationNm?'
    bus_type : str #'busType' -> 0 일반, 1 저상, 2 굴절
    arrival: str # 'arrmsg'
    is_last : bool #'isLast' -> 1 is 막차
    is_full : bool

    def __str__(self) -> str:
        return f"{self.destination}행 {self.arrival}"


@dataclass
class BusArrivalInfo:
    """Holds the next two arrival messages for a single direction/stop."""
    first: BusInfo | None
    second: BusInfo | None

    
    def __str__(self) -> str:
        return f"첫 번째: {self.first} | 두 번째: {self.second}"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class TransitAPIError(Exception):
    """Raised when an API call returns an error response."""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_json(url: str) -> dict:
    """
    Make a GET request and return the parsed JSON body.
    Raises:
        TransitAPIError: if the HTTP request fails or the body isn't valid JSON.
    """
    try:
        response = requests.get(url, timeout=10)  # timeout prevents hanging forever
        response.raise_for_status()               # raises for 4xx / 5xx HTTP errors
        return response.json()
    except requests.exceptions.JSONDecodeError as exc:
        raise TransitAPIError("Response was not valid JSON.") from exc
    except requests.exceptions.RequestException as exc:
        raise TransitAPIError(f"HTTP request failed: {exc}") from exc


def _save_json(data: dict, filename: str) -> None:
    """Optionally write a raw API response to disk for debugging."""
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)


def get_bus_arrivals(api_key: str, station_id: str, route_id: str) -> ArrivalInfo:
    """
    Fetch real-time bus arrival data for a specific stop on a route.

    The API returns *all* stops on the route at once; we filter to the one
    matching `station_id`.  Each stop entry already carries two arrival
    messages (arrmsg1 / arrmsg2), so we return both.

    Args:
        api_key:    Seoul Bus Open API authentication key.
        station_id: Numeric ID of the bus stop, e.g. "111000937".
        route_id:   Numeric ID of the bus route,  e.g. "100100352".

    Returns:
        An ArrivalInfo with the next two bus arrival times.

    Raises:
        TransitAPIError: on network failure, API error, or stop not found.
    """
    url = (
        f"{BUS_BASE_URL}/getArrInfoByRouteAll"
        f"?ServiceKey={api_key}&busRouteId={route_id}&resultType=json"
    )
    data = _get_json(url)
    _save_json(data, "bus.json")

    header = data.get("msgHeader", {})
    if header.get("headerCd") != "0":
        raise TransitAPIError(f"Bus API error: {header.get('headerMsg', 'Unknown error')}")

    stops = data.get("msgBody", {}).get("itemList", [])

    # Using next() with a generator is the idiomatic Python way to find the
    # first matching item in a list without writing an explicit for-loop.
    matched_stop = next(
        (stop for stop in stops if stop.get("stId") == station_id),
        None,  # default value if nothing matches
    )

    if matched_stop is None:
        raise TransitAPIError(f"Station ID '{station_id}' not found in route '{route_id}'.")

    return ArrivalInfo(
        first=matched_stop.get("arrmsg1", "정보 없음"),
        second=matched_stop.get("arrmsg2", "정보 없음"),
    )