# seoul-realtime-arrival

A Python wrapper library for fetching real-time arrival information from Seoul's public transportation APIs — covering both subway (metro) and bus lines.

서울특별시 대중교통(버스 및 지하철) API에 접근하기 위한 Python wrapper입니다.

---

## Features

- Real-time subway arrival info by station name
- Real-time bus arrival info by stop ID and route ID
- Structured return types (dataclasses) for easy downstream use
- Supports express/rapid trains, last train flags, and bus type classification

---

## Requirements

### Python Dependencies

```bash
pip install requests
```

### API Keys

This library requires two separate API keys:

| Service | Source |
|---|---|
| **Metro (Subway)** | [Seoul Open Data Hall (서울열린데이터광장)](https://data.seoul.go.kr/dataList/OA-12764/F/1/datasetView.do) |
| **Bus** | [Public Data Portal (공공데이터포털)](https://www.data.go.kr/data/15000314/openapi.do) |

While not mandatory, recommended to use environment files to safely protect sensitive information like API keys. You can do this by using python's dotenv package.
Please refer to [pypi](https://pypi.org/project/python-dotenv/) for more information.

---

## Usage

### Metro (Subway) — `metro.py`

**Function:** `get_metro_arrivals(api_key, station_name, store_data=False)`

| Parameter | Type | Description |
|---|---|---|
| `api_key` | `str` | Seoul Subway Open API key |
| `station_name` | `str` | Station name in Korean (e.g. `"서울"`) — must match the API's internal name exactly |
| `store_data` | `bool` | If `True`, saves the raw API response to `metro.json` (default: `False`) |

**Returns:** `dict[str, MetroArrivalInfo]`

Each key is a line name (e.g. `"3호선"`), and the value is a `MetroArrivalInfo` dataclass.

#### Return Type Structure

```
MetroArrivalInfo
├── inbound:          TrainInfo | None   # 상행 / 내선 (towards city-centre / clockwise)
├── outbound:         TrainInfo | None   # 하행 / 외선 (away from city-centre / counter-clockwise)
├── express_inbound:  TrainInfo | None   # Express/rapid train, inbound direction
└── express_outbound: TrainInfo | None   # Express/rapid train, outbound direction

TrainInfo
├── id:          str | None   # Train number (4-digit)
├── type:        str | None   # Train type (e.g. 일반, 급행, ITX)
├── destination: str | None   # Final stop (terminus)
├── arrival:     str | None   # Arrival status message
└── is_last:     bool | None  # True if this is the last train of the day
```

**Example:**

```python
import os
import dotenv
from metro import get_metro_arrivals

dotenv.load_dotenv()
api_key = os.environ["METRO_KEY"]

arrivals = get_metro_arrivals(api_key, "홍대입구")

for line, info in arrivals.items():
    print(f"=== {line} ===")
    print(info)
```

**Example output:**
```
=== 2호선 ===
성수행 3242열차 전역 도착
성수행 2249열차 4분 후

=== 경의중앙선 ===
문산행 5078열차 [3]번째 전역 (효창공원앞)
용문행 5085열차 [7]번째 전역 (강매)

=== 공항철도 ===
인천공항2터미널행 A2155열차 [2]번째 전역 (서울)
인천공항2터미널급행 A1029열차 홍대입구 출발
서울행 A3022열차 전역 출발
서울급행 A1032열차 [7]번째 전역 (영종)
```

---

### Bus — `bus.py`

**Function:** `get_bus_arrivals(api_key, station_id, route_id, store_data=False)`

| Parameter | Type | Description |
|---|---|---|
| `api_key` | `str` | Seoul Bus Open API key |
| `station_id` | `str` | Numeric bus stop ID (e.g. `"111000937"`) |
| `route_id` | `str` | Numeric bus route ID (e.g. `"100100352"`) |
| `store_data` | `bool` | If `True`, saves the raw API response to `bus.json` (default: `False`) |

> **Note:** The bus API does not support stop name lookups. You must provide the numeric `station_id` and `route_id` directly. These can be found through Seoul's public data portal ([Bus Station Location Information](https://data.seoul.go.kr/dataList/OA-15067/S/1/datasetView.do), [Bus Line information](https://data.seoul.go.kr/dataList/OA-15262/F/1/datasetView.do)).

**Returns:** `BusArrivalInfo`

#### Return Type Structure

```
BusArrivalInfo
├── station_name: str | None      # Bus stop name
├── line_number:  str | None      # Bus route number
├── arrival_1:    BusInfo | None  # Next arriving bus (1st)
└── arrival_2:    BusInfo | None  # Next arriving bus (2nd)

BusInfo
├── current_station: str | None   # Current location of the bus
├── bus_type:        str | None   # '0' = 일반, '1' = 저상 (low-floor), '2' = 굴절 (articulated)
├── arrival:         str | None   # Arrival time/status message
└── is_last:         bool | None  # True if this is the last bus of the day
```

**Example:**

```python
import os
import dotenv
from bus import get_bus_arrivals

dotenv.load_dotenv()
api_key = os.environ["BUS_KEY"]

info = get_bus_arrivals(api_key, station_id="113000079", route_id="100100288")
print(info)
```

**Example output:**
```
서강대학교 5714
[저상] 3분23초후[3번째 전] (서강대후문.마포아트센터)
[저상] 14분56초후[9번째 전] (동교동삼거리)
```

---

## Error Handling

Both modules raise `TransitAPIError` (a custom exception) when:
- The network request fails
- The API returns an error code
- Expected fields are missing from the response
- The station name or stop ID is not found

```python
from metro import get_metro_arrivals, TransitAPIError

try:
    arrivals = get_metro_arrivals(api_key, "미쿠")
except TransitAPIError as e:
    print(f"API error: {e}")
```
**Example output:**
```
API error: [INFO-200] (HTTP 500) 해당하는 데이터가 없습니다.
```
---

## Supported Subway Lines

| Line ID | Line Name |
|---|---|
| 1001 | 1호선 |
| 1002 | 2호선 |
| 1003 | 3호선 |
| 1004 | 4호선 |
| 1005 | 5호선 |
| 1006 | 6호선 |
| 1007 | 7호선 |
| 1008 | 8호선 |
| 1009 | 9호선 |
| 1061 | 중앙선 |
| 1063 | 경의중앙선 |
| 1065 | 공항철도 |
| 1067 | 경춘선 |
| 1075 | 수인분당선 |
| 1077 | 신분당선 |
| 1081 | 경강선 |
| 1092 | 우이신설선 |
| 1093 | 서해선 |
| 1032 | GTX-A |

While the API supports almost all metro lines, some lines are not listed in the API and as such information cannot be retrieved from them. This is an API issue that needs to be solved by the rail authorities.