"""
Seoul Metropolitan Subway Real-Time Arrival Checker
Fetches live arrival info from Seoul Open API for the subway.

Environment variables required:
    METRO_KEY - Seoul Subway Open API key
"""

import json
import os
from dataclasses import dataclass

import dotenv
import requests

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

METRO_BASE_URL = "http://swopenAPI.seoul.go.kr/api/subway"

# Subway direction labels used by the API
INBOUND_LABELS = {"상행", "내선"}   # towards city-centre / clockwise
OUTBOUND_LABELS = {"하행", "외선"}  # away from city-centre / counter-clockwise
#Note: counter-clockwise destinations are only used by Line 2.

# Maximum number of queries per API call for metro (ex. 0~6)
MAX_METRO_COUNT = '20'

metro_line_id_lookup = { '1001':'1호선', '1002':'2호선', '1003':'3호선', '1004':'4호선', '1005':'5호선',
                     '1006':'6호선', '1007':'7호선', '1008':'8호선', '1009':'9호선', '1061':'중앙선', 
                     '1063':'경의중앙선', '1065':'공항철도', '1067':'경춘선', '1075':'수인분당선',
                     '1077':'신분당선', '1092':'우이신설선', '1093':'서해선', '1081':'경강선',
                     '1032':'GTX-A' }
# lookup table (dictionary) for line IDs and line string names

# ---------------------------------------------------------------------------
# Return types
# ---------------------------------------------------------------------------


@dataclass
class TrainInfo:
    """
    TrainInfo stores the information of an individual train.

    Attributes:
        id - the train's unique ID, a 4-digit number stored as a string
        type - the train's type, such as 일반(normal), 급행/특급(express)
        destination - the train's final stop (terminus)
        arrival - the arrival status of the train
        is_last - boolean value to represent if a train is the last for the day (True : last / None : not last)
        
    """
    
    id: str | None
    type: str | None
    destination: str | None
    arrival: str | None
    is_last: bool | None

    # Class constructor - if no parameters are passed then everything is set to None.
    def __init__(self, id=None, train_type=None, destination=None, arrival=None, is_last=None):
        self.id = id
        self.type = train_type
        self.destination = destination
        self.arrival = arrival
        self.is_last = is_last

    # hash function needed for dictionary lookup
    def __hash__(self):
        return hash(self.id)
        # every train has a unique train_id, so there is no need to hash other variables
    
    def __str__(self) -> str:
        return f"{"[막차] " if self.is_last is True else ""}{self.destination}{"급행" if self.type!="일반" else "행"} {self.id}열차 {self.arrival}"

#MetroArrivalInfo stores the arrival information for one station, one line.
# consists of 4 TrainInfo class variables
@dataclass
class MetroArrivalInfo:
    """
    MetroArrivalInfo stores the arrival information of an individual line.
    Each attribute is of class TrainInfo.
    
    Attributes:
        inbound - self explanatory
        outbound - self explanatory
        express_inbound - only filled if there is a corresponding express train, or else set to None
        express_outbound - only filled if there is a corresponding express train, or else set to None
        
    """
    inbound: TrainInfo | None
    outbound: TrainInfo | None
    express_inbound: TrainInfo | None
    express_outbound: TrainInfo | None

    def __init__(self):
        self.inbound = None
        self.outbound = None
        self.express_inbound = None
        self.express_outbound = None

    #check if all attributes have been assigned a TrainInfo.
    def check_full(self) -> bool:
        return (self.inbound != None) and (self.outbound != None) and (self.express_inbound != None) and (self.express_outbound != None)
    

    def __str__(self) -> str:
        return_str = ""
        if self.inbound is not None: return_str += str(self.inbound) + '\n'
        if self.express_inbound is not None: return_str += str(self.express_inbound) + '\n'
        if self.outbound is not None: return_str += str(self.outbound) + '\n'
        if self.express_outbound is not None: return_str += str(self.express_outbound)
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


# ---------------------------------------------------------------------------
# Metro (subway)
# ---------------------------------------------------------------------------

def get_metro_arrivals(api_key: str, station_name: str, store_data=False) -> dict[str, list]:
    """
    Fetch real-time subway arrival data for a Seoul Metro station.

    The API returns arrivals for both directions mixed together in one list.
    We scan through them and pick the *first* entry for each direction & train type.

    Args:
        api_key:      Seoul Subway OpenAPI authentication key.
        station_name: Korean station name, e.g. "녹번".
        # IMPORTANT: Metro station names must exactly match the internal API station names, 
        # or else the API will raise error INFO-200.

    Returns:
        A dictionary of arrival information, where each key-value pair is {str : MetroArrivalInfo} with 
        the key being the line name and the value being an TrainInfo instance.
        MetroArrivalInfo is a a dataclass with 4 attributes(inbound/outbound/express inbound/expreses outbound), each of type TrainInfo.
        TrainInfo is a dataclass with 5 attributes, id, train_type, destination, arrival, is_last.
        
        You can print the return value simply by iterating over the dictionary and printing the value - 
        class internal __str__ methods will return the data in string format.

        example)
        for key, value in data.items():
            print(value)
        
            
    Raises:
        TransitAPIError: on network failure or an API-level error.
    """
    url = (
        f"{METRO_BASE_URL}/{api_key}/json/realtimeStationArrival"
        f"/0/{MAX_METRO_COUNT}/{station_name}"
        )
    
    data = _get_json(url)
    
    if (store_data):
        _save_json(data, "metro.json")

    # --- Error detection ---
    # Success responses wrap responses status inside 'errorMessage', 
    # with requested information inside 'msgBody'.
    # However, error responses do not have an 'errorMessage' wrapper at all,
    #  but only has response related key-value pairs at the top level.
    # (the API is a bit confusingly structured).
    # Thus, we check for the wrapper 'errorMessage' first; 
    # if it's missing, we're looking at an error.
    # If 'errorMessage' exists, then we look at the contents of the wrapper 
    # to determine if we got a valid response.

    # Successful responses will have code 'INFO-000' inside the 'errorMessage' wrapper.
    # Anything else is an error.

    if "errorMessage" in data:
        error_msg = data["errorMessage"]
        if error_msg.get("code") != "INFO-000":
            code = error_msg.get("code", "UNKNOWN")
            message = error_msg.get("message", "No message provided.")
            raise TransitAPIError(f"[{code}] {message}")
    else:
        # Flat error response (no wrapper) — extract fields directly from the top level
        code = data.get("code", "UNKNOWN")
        message = data.get("message", "No message provided.")
        status = data.get("status", "N/A")
        raise TransitAPIError(f"[{code}] (HTTP {status}) {message}")
    

    ##TODO: Check transfer lines cnt ('trnsitCo')
    # -> group by subwayId (each pair)
    # dict (str? : list[MetroArrivalInfo])
    #

    arrivals = data.get("realtimeArrivalList", [])

    arrival_data = {}
    # dictionary structured as [str, MetroArrivalInfo]
    # MetroArrivalInfo is an class that stores multiple instances of TrainInfo,
    # specifically 4 - inbound, outbound, inbound_express, outbound_express
    #
    # metro_data is structured as a dictionary of string to TrainInfo pairs.
    #
    # metro_data : "Line A" : MetroArrivalInfo (TrainInfo, TrainInfo, TrainInfo, TrainInfo)
    #              "Line B" : MetroArrivalInfo (TrainInfo, TrainInfo, TrainInfo, TrainInfo)
    #              ...

    line_str = arrivals[0].get("subwayList", None)
    # get a list of all lines that stop at this station
    # "subwayList" is a string literal that holds the line IDs of subway lines
    # that stop at the station, separated by commas

    if line_str == None:
        raise TransitAPIError(f"Necessary parameter 'subwayList' missing in JSON.") 
    else:
        line_list = line_str.split(sep=',')
        for line in line_list:
            metro_line_str = metro_line_id_lookup.get(line, None)
            if metro_line_str is None:
                raise TransitAPIError(f"Unknown subway line number.") 
            arrival_data[metro_line_str] = MetroArrivalInfo()
            # initialize dictionary with empty instances of MetroArrivalInfo.
            # After this step, all MetroArrivalInfo classes instantiated will have None as the member values.

    for entry in arrivals:
        line_id = entry.get("subwayId", None) #get current line as ID
        line_name = metro_line_id_lookup.get(line_id, None) # turn line ID to a line 'string' (ex. 1001 -> 1호선)
    
        if (line_name is None):
            raise TransitAPIError(f"Some parameters missing in JSON.")
        else:
            if line_name in arrival_data:
                if (arrival_data[line_name].check_full()):
                    continue
                else:
                    #get current train information from JSON
                    direction = entry.get("updnLine", None)
                    arrival_msg = entry.get("arvlMsg2", "정보 없음")
                    destination = entry.get("bstatnNm", None)
                    train_id = entry.get("btrainNo", None)
                    train_type = entry.get("btrainSttus", "정보 없음")

                    if (entry.get("lstcarAt") == '1'): is_last = True
                    else: is_last = False
                    
                    # 'updnLine' - indicates the direction of the train
                    #  (up/down or circle inner/circle outer)
                    # 'arvlMsg2' - the arrival status message of the train.
                    # (Note: another message 'arvlMsg3' also exists, but 'arvlMsg2' usually
                    # has more information compared to 'arvlMsg3')
                    # 'bstatnNm' - the final stop (terminus) of the current train
                    # 'btrainNo' - the train number (train id) of the current train
                    # 'btrainSttus' - the train type (normal, express, rapid, ITX etc)

                    # We only need the *first* match per direction & train type, so when we
                    # have a train that fits an empty member in the ArrivalInfo class, we set the member
                    # to an instance of the TrainInfo class.

                    #Inbound
                    if direction in INBOUND_LABELS:
                        
                        if arrival_data[line_name].inbound is None and train_type == "일반": #Normal
                            arrival_data[line_name].inbound = TrainInfo(train_type=train_type, id=train_id, arrival=arrival_msg, destination=destination,is_last=is_last)
                        
                        elif arrival_data[line_name].express_inbound is None and train_type != "일반": #Express/Rapid
                            arrival_data[line_name].express_inbound = TrainInfo(train_type=train_type, id=train_id, arrival=arrival_msg, destination=destination,is_last=is_last)
                    
                    #Outbound
                    elif direction in OUTBOUND_LABELS:
                        
                        if arrival_data[line_name].outbound is None and train_type == "일반": #Normal
                            arrival_data[line_name].outbound = TrainInfo(train_type=train_type, id=train_id, arrival=arrival_msg, destination=destination,is_last=is_last)
                        
                        elif arrival_data[line_name].express_outbound is None and train_type != "일반": #Express/Rapid
                            arrival_data[line_name].express_outbound = TrainInfo(train_type=train_type, id=train_id, arrival=arrival_msg, destination=destination,is_last=is_last)
                        
                    else:
                        raise TransitAPIError(f"Could not find arrival data for station: {station_name}")
            else:
                raise TransitAPIError(f"Line parameter mismatch.")
            
    return arrival_data