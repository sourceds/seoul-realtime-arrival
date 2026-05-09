"""
Seoul Bus Real-Time Arrival Checker
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

bus_type_lookup = { '0' : '일반', '1' : '저상', '2' : '굴절' }

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------

@dataclass
class BusInfo:
    #Holds the arrival messages for a single bus/train.
    
    current_station: str | None # 'stationNm?'
    bus_type : str | None #'busType' -> 0 일반, 1 저상, 2 굴절
    arrival: str | None # 'arrmsg'
    is_last : bool | None #'isLast' -> 1 is 막차

    def __init__(self, destination=None, current_station=None, bus_type=None, arrival=None, is_last=None):
        self.current_station=current_station
        self.bus_type=bus_type
        self.arrival=arrival
        self.is_last=is_last

    def __str__(self) -> str:
        return_str = (
                f"{('[' + bus_type_lookup[self.bus_type] + '] ') if self.bus_type != ('0' or None) else ""}"
                f"{self.arrival} "
                f"({self.current_station})"
        )
        return return_str


@dataclass
class BusArrivalInfo:
    """Holds the next two bus data for a single line & stop."""
    station_name: str | None
    line_number: str | None
    arrival_1: BusInfo | None
    arrival_2: BusInfo | None

    def __init__(self):
        self.arrival_1 = None
        self.arrival_2 = None
    
    def __str__(self) -> str:
        return_str = f"{self.station_name} {self.line_number}\n"
        if self.arrival_1 is not None: return_str += str(self.arrival_1) + '\n'
        if self.arrival_2 is not None: return_str += str(self.arrival_2)
        return return_str


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


def get_bus_arrivals(api_key: str, station_id: str, route_id: str, store_data=False) -> BusArrivalInfo:
    """
    Fetch real-time bus arrival data for a specific stop on a route.

    The API returns the *entire* arrival information for the specified line; we filter to the one
    matching `station_id`.  Each stop entry carries the arrival data of the next two buses expected
    to arrive.

    Args:
        api_key:    Seoul Bus Open API authentication key.
        station_id: Numeric ID of the bus stop, e.g. "111000937".
        route_id:   Numeric ID of the bus route,  e.g. "100100352".
    Note: due to the nature of the bus API, station_id and route_id must be provided by
    the user (bus API does not do a station name lookup)

    Returns:
        A BusArrivalInfo with the next two bus arrival times.

    Raises:
        TransitAPIError: on network failure, API error, or stop not found.
    """

    url = (
        f"{BUS_BASE_URL}/getArrInfoByRouteAll"
        f"?ServiceKey={api_key}&busRouteId={route_id}&resultType=json"
    )

    data = _get_json(url)
    
    if (store_data):
        _save_json(data, "metro.json")

    header = data.get("msgHeader", {})
    if header.get("headerCd") != "0":
        raise TransitAPIError(f"Bus API error: {header.get('headerMsg', 'Unknown error')}")

    stops = data.get("msgBody", {}).get("itemList", [])

    return_data = BusArrivalInfo()

    # Using next() with a generator to find the first matching station in the json
    # can be replaced with an explicit for-loop
    matched_stop = next(
        (stop for stop in stops if stop.get("stId") == station_id),
        None,  # default value if nothing matches
    )

    if matched_stop is None:
        raise TransitAPIError(f"Station ID '{station_id}' not found in route '{route_id}'.")
    else:
        #arrival_1
        try:
            return_data.station_name = matched_stop['stNm']
            return_data.line_number = matched_stop['rtNm']

            return_data.arrival_1 = BusInfo(
                arrival=matched_stop['arrmsg1'],
                is_last=True if matched_stop['isLast1'] =='1' else '0',
                bus_type=matched_stop['busType1'],
                current_station = matched_stop['stationNm1']
            )

            return_data.arrival_2 = BusInfo(
                arrival=matched_stop['arrmsg2'],
                is_last=True if matched_stop['isLast2'] =='1' else '0',
                bus_type=matched_stop['busType2'],
                current_station = matched_stop['stationNm2']
            )

        except KeyError as e:
            raise TransitAPIError(f"Required field not found in JSON: {e}")

    return return_data