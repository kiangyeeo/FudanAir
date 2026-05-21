from __future__ import annotations

import argparse
import csv
import json
import random
import re
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from itertools import permutations
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_AIRPORTS_CSV = PROJECT_ROOT / "backend" / "data" / "airports.csv"
DEFAULT_AIRCRAFT_CSV = PROJECT_ROOT / "backend" / "data" / "aircraft_types.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "generated_data" / "mu_fm_flights"
DEFAULT_AIRPORT_SOURCE_URL = "https://raw.githubusercontent.com/mwgg/Airports/master/airports.json"

AIRLINES = {"MU", "FM"}
AIRCRAFT_MODELS = ("A319", "A320", "A321", "A332", "A333", "A359", "B738", "B789", "C919", "ARJ21")
NARROW_BODY = ("A319", "A320", "A321", "B738", "C919", "ARJ21")
WIDE_BODY = ("A332", "A333", "A359", "B789")
TERMINALS = ("T1", "T2", "T3")
AIRCRAFT_SEATS = {
    "A319": (120, 8),
    "A320": (150, 8),
    "A321": (182, 12),
    "A332": (234, 30),
    "A333": (262, 30),
    "A359": (256, 40),
    "B737": (144, 8),
    "B738": (162, 8),
    "B789": (258, 28),
    "C919": (156, 8),
    "ARJ21": (90, 0),
}
DOMESTIC_AIRPORT_FALLBACK = {
    "PEK": ("北京首都国际机场", "北京"),
    "PKX": ("北京大兴国际机场", "北京"),
    "PVG": ("上海浦东国际机场", "上海"),
    "SHA": ("上海虹桥国际机场", "上海"),
    "CAN": ("广州白云国际机场", "广州"),
    "SZX": ("深圳宝安国际机场", "深圳"),
    "CTU": ("成都双流国际机场", "成都"),
    "TFU": ("成都天府国际机场", "成都"),
    "KMG": ("昆明长水国际机场", "昆明"),
    "XIY": ("西安咸阳国际机场", "西安"),
    "CKG": ("重庆江北国际机场", "重庆"),
    "HGH": ("杭州萧山国际机场", "杭州"),
    "NKG": ("南京禄口国际机场", "南京"),
    "WUH": ("武汉天河国际机场", "武汉"),
    "CSX": ("长沙黄花国际机场", "长沙"),
    "TAO": ("青岛胶东国际机场", "青岛"),
    "XMN": ("厦门高崎国际机场", "厦门"),
    "FOC": ("福州长乐国际机场", "福州"),
    "DLC": ("大连周水子国际机场", "大连"),
    "SHE": ("沈阳桃仙国际机场", "沈阳"),
    "HRB": ("哈尔滨太平国际机场", "哈尔滨"),
    "CGO": ("郑州新郑国际机场", "郑州"),
    "TNA": ("济南遥墙国际机场", "济南"),
    "URC": ("乌鲁木齐地窝堡国际机场", "乌鲁木齐"),
    "SYX": ("三亚凤凰国际机场", "三亚"),
    "HAK": ("海口美兰国际机场", "海口"),
    "NNG": ("南宁吴圩国际机场", "南宁"),
    "KWE": ("贵阳龙洞堡国际机场", "贵阳"),
    "LHW": ("兰州中川国际机场", "兰州"),
    "TYN": ("太原武宿国际机场", "太原"),
    "HET": ("呼和浩特白塔国际机场", "呼和浩特"),
    "LXA": ("拉萨贡嘎机场", "拉萨"),
    "INC": ("银川河东国际机场", "银川"),
    "XNN": ("西宁曹家堡国际机场", "西宁"),
}
USER_AGENTS = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_6) AppleWebKit/605.1.15 Version/17.0 Safari/605.1.15",
)


@dataclass(frozen=True)
class Airport:
    code: str
    name: str = ""
    city: str = ""


@dataclass(frozen=True)
class AircraftType:
    model: str
    economy_seats: int
    first_seats: int


@dataclass
class Flight:
    flight_no: str
    scheduled_departure: str | None
    scheduled_arrival: str | None
    dep_airport_code: str
    arr_airport_code: str
    airline_code: str
    aircraft_model: str | None = None
    dep_terminal: str | None = None
    arr_terminal: str | None = None
    fuel_infra_fee: int | None = None
    weekdays: set[int] | None = None
    stopovers: list[str] | None = None
    crawled: bool = False


def main() -> None:
    args = parse_args()
    random.seed(args.seed)

    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    airports = crawl_domestic_airports(args)
    flights = crawl_many(airports, args)
    discovered_models = {flight.aircraft_model for flight in flights if flight.aircraft_model}
    aircraft_types = build_aircraft_types(discovered_models, args.aircraft_csv)
    aircraft_models = sorted(aircraft_types)

    if len(flights) < args.min_flights:
        flights.extend(generate_reasonable_flights(airports, aircraft_models, args.min_flights - len(flights), flights))

    normalized = normalize_flights(flights, airports, aircraft_models)
    write_base_csvs(airports, aircraft_types, output_dir)
    write_csvs(normalized, output_dir)
    write_summary(normalized, output_dir)

    print(f"wrote {len(airports)} airports, {len(aircraft_types)} aircraft types, {len(normalized)} flights to {output_dir}")
    print(f"  {output_dir / 'airports.csv'}")
    print(f"  {output_dir / 'aircraft_types.csv'}")
    print(f"  {output_dir / 'flights.csv'}")
    print(f"  {output_dir / 'flight_weekdays.csv'}")
    print(f"  {output_dir / 'flight_stopovers.csv'}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl and complete China Eastern (MU) and Shanghai Airlines (FM) flight CSVs.",
    )
    parser.add_argument("--airports-csv", type=Path, default=DEFAULT_AIRPORTS_CSV)
    parser.add_argument("--aircraft-csv", type=Path, default=DEFAULT_AIRCRAFT_CSV)
    parser.add_argument("--airport-source-url", default=DEFAULT_AIRPORT_SOURCE_URL)
    parser.add_argument("--offline", action="store_true", help="skip network airport source and use local/fallback airports")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--date", default=(date.today() + timedelta(days=7)).isoformat())
    parser.add_argument("--days", type=int, default=7, help="search this many dates to infer weekdays")
    parser.add_argument("--max-routes", type=int, default=0, help="0 means try all airport pairs")
    parser.add_argument("--sleep", type=float, default=0.25)
    parser.add_argument("--timeout", type=float, default=10)
    parser.add_argument("--min-flights", type=int, default=1200)
    parser.add_argument("--seed", type=int, default=20260517)
    return parser.parse_args()


def load_airports(path: Path) -> dict[str, Airport]:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        airports: dict[str, Airport] = {}
        for row in reader:
            code = first_value(row, "iata_code", "airport_code", "code").upper()
            if re.fullmatch(r"[A-Z]{3}", code):
                airports[code] = Airport(
                    code=code,
                    name=first_value(row, "airport_name", "name"),
                    city=first_value(row, "city_name", "city"),
                )
    return airports


def crawl_domestic_airports(args: argparse.Namespace) -> dict[str, Airport]:
    airports: dict[str, Airport] = {}
    if not args.offline:
        airports.update(crawl_airports_from_public_source(args.airport_source_url, args.timeout))
    airports.update({code: Airport(code, name, city) for code, (name, city) in DOMESTIC_AIRPORT_FALLBACK.items()})
    airports.update(load_airports(args.airports_csv))
    if not airports:
        raise ValueError("no domestic airports available; check --airports-csv or network source")
    return dict(sorted(airports.items()))


def crawl_airports_from_public_source(url: str, timeout: float) -> dict[str, Airport]:
    data = fetch_json(url, timeout)
    airports: dict[str, Airport] = {}
    if not isinstance(data, dict):
        return airports
    for item in data.values():
        if not isinstance(item, dict):
            continue
        if str(item.get("country", "")).upper() != "CN":
            continue
        code = normalize_airport_code(str(item.get("iata", "")))
        if not code:
            continue
        name = str(item.get("name") or "").strip()
        city = str(item.get("city") or "").strip()
        airports[code] = Airport(code=code, name=name or f"{code} Airport", city=city or code)
    return airports


def build_aircraft_types(discovered_models: set[str], path: Path) -> dict[str, AircraftType]:
    models = set(AIRCRAFT_MODELS) | {model for model in discovered_models if model}
    if not path.exists():
        return {model: aircraft_type_for_model(model) for model in sorted(models)}

    aircraft_types = {model: aircraft_type_for_model(model) for model in models}
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            model = first_value(row, "model", "aircraft_model").upper()
            if not model:
                continue
            economy = int(float(first_value(row, "economy_seats") or AIRCRAFT_SEATS.get(model, (150, 8))[0]))
            first = int(float(first_value(row, "first_seats") or AIRCRAFT_SEATS.get(model, (150, 8))[1]))
            aircraft_types[model] = AircraftType(model, economy, first)
    return dict(sorted(aircraft_types.items()))


def aircraft_type_for_model(model: str) -> AircraftType:
    economy, first = AIRCRAFT_SEATS.get(model, (150, 8))
    return AircraftType(model, economy, first)


def fetch_json(url: str, timeout: float) -> Any:
    req = Request(
        url,
        headers={"User-Agent": random.choice(USER_AGENTS)},
        method="GET",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError):
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def crawl_many(airports: dict[str, Airport], args: argparse.Namespace) -> list[Flight]:
    routes = list(permutations(sorted(airports), 2))
    random.shuffle(routes)
    if args.max_routes > 0:
        routes = routes[: args.max_routes]

    start = datetime.strptime(args.date, "%Y-%m-%d").date()
    by_key: dict[tuple[str, str, str], Flight] = {}

    for idx, (dep, arr) in enumerate(routes, start=1):
        for offset in range(args.days):
            day = start + timedelta(days=offset)
            for flight in query_ctrip(dep, arr, day, args.timeout):
                if flight.airline_code not in AIRLINES:
                    continue
                if flight.dep_airport_code not in airports or flight.arr_airport_code not in airports:
                    continue
                key = (flight.flight_no, flight.dep_airport_code, flight.arr_airport_code)
                existing = by_key.get(key)
                weekday = day.isoweekday()
                if existing:
                    existing.weekdays = (existing.weekdays or set()) | {weekday}
                else:
                    flight.weekdays = {weekday}
                    flight.crawled = True
                    by_key[key] = flight
        if args.sleep:
            time.sleep(args.sleep)
        if idx % 100 == 0:
            print(f"checked {idx}/{len(routes)} routes, crawled {len(by_key)} flights")
    return list(by_key.values())


def query_ctrip(dep: str, arr: str, flight_date: date, timeout: float) -> list[Flight]:
    """Best-effort parser for Ctrip's public flight-search JSON.

    The endpoint occasionally changes shape, so the parser recursively scans
    the returned JSON for objects that look like flight segments.
    """
    payload = {
        "flightWay": "Oneway",
        "classType": "ALL",
        "hasChild": False,
        "hasBaby": False,
        "searchIndex": 1,
        "airportParams": [
            {
                "dcity": dep,
                "acity": arr,
                "date": flight_date.isoformat(),
            }
        ],
    }
    req = Request(
        "https://flights.ctrip.com/international/search/api/search/batchSearch",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "User-Agent": random.choice(USER_AGENTS),
            "Referer": "https://flights.ctrip.com/",
        },
        method="POST",
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except (HTTPError, URLError, TimeoutError, OSError):
        return []

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return []
    return extract_flights(data, dep, arr)


def extract_flights(data: Any, expected_dep: str, expected_arr: str) -> list[Flight]:
    result: list[Flight] = []
    for obj in walk_dicts(data):
        flight_no = normalize_flight_no(
            first_value(
                obj,
                "flightNo",
                "flight_no",
                "flightNumber",
                "flightNumberText",
                "craftTripNo",
            )
        )
        if not flight_no or flight_no[:2] not in AIRLINES:
            continue

        dep = normalize_airport_code(first_value(obj, "depAirportCode", "dport", "dcity", "depCode"))
        arr = normalize_airport_code(first_value(obj, "arrAirportCode", "aport", "acity", "arrCode"))
        dep = dep or expected_dep
        arr = arr or expected_arr
        if dep == arr:
            continue

        result.append(
            Flight(
                flight_no=flight_no,
                scheduled_departure=normalize_time(first_value(obj, "depTime", "departureTime", "dt")),
                scheduled_arrival=normalize_time(first_value(obj, "arrTime", "arrivalTime", "at")),
                dep_airport_code=dep,
                arr_airport_code=arr,
                dep_terminal=normalize_terminal(first_value(obj, "depTerminal", "departureTerminal")),
                arr_terminal=normalize_terminal(first_value(obj, "arrTerminal", "arrivalTerminal")),
                airline_code=flight_no[:2],
                aircraft_model=normalize_aircraft(first_value(obj, "aircraftCode", "craftTypeCode", "craftType")),
                stopovers=extract_stopovers(obj),
            )
        )
    return result


def normalize_flights(flights: list[Flight], airports: dict[str, Airport], aircraft_models: list[str]) -> list[Flight]:
    seen: set[str] = set()
    normalized: list[Flight] = []
    for flight in sorted(flights, key=lambda x: (x.airline_code, x.flight_no, x.dep_airport_code, x.arr_airport_code)):
        flight.flight_no = unique_flight_no(flight.flight_no, seen)
        seen.add(flight.flight_no)
        fill_missing(flight, airports, aircraft_models)
        normalized.append(flight)
    return normalized


def fill_missing(flight: Flight, airports: dict[str, Airport], aircraft_models: list[str]) -> None:
    if not flight.scheduled_departure:
        flight.scheduled_departure = random_time()
    if not flight.scheduled_arrival:
        flight.scheduled_arrival = arrival_after(flight.scheduled_departure, flight.dep_airport_code, flight.arr_airport_code)
    if flight.fuel_infra_fee is None:
        flight.fuel_infra_fee = random.choice((50, 60, 70, 90))
    if not flight.dep_terminal:
        flight.dep_terminal = random.choice(TERMINALS)
    if not flight.arr_terminal:
        flight.arr_terminal = random.choice(TERMINALS)
    if flight.aircraft_model not in aircraft_models:
        flight.aircraft_model = choose_aircraft(flight.dep_airport_code, flight.arr_airport_code, aircraft_models)
    if not flight.weekdays:
        flight.weekdays = choose_weekdays()
    if flight.stopovers is None:
        flight.stopovers = []
    flight.stopovers = [code for code in flight.stopovers if code in airports and code not in {flight.dep_airport_code, flight.arr_airport_code}]


def generate_reasonable_flights(
    airports: dict[str, Airport],
    aircraft_models: list[str],
    count: int,
    existing: list[Flight],
) -> list[Flight]:
    airport_codes = sorted(airports)
    used = {f.flight_no for f in existing}
    generated: list[Flight] = []
    hubs = [code for code in ("PVG", "SHA", "PKX", "PEK", "CAN", "SZX", "CTU", "TFU", "XIY", "KMG") if code in airports]
    if not hubs:
        hubs = airport_codes[: min(12, len(airport_codes))]

    attempts = 0
    while len(generated) < count and attempts < count * 30:
        attempts += 1
        airline = random.choices(("MU", "FM"), weights=(8, 2), k=1)[0]
        dep = random.choice(hubs if random.random() < 0.65 else airport_codes)
        arr = random.choice(airport_codes)
        if dep == arr:
            continue
        flight_no = make_flight_no(airline, used)
        used.add(flight_no)
        dep_time = random_time()
        stopovers = choose_stopovers(dep, arr, airport_codes) if random.random() < 0.08 else []
        generated.append(
            Flight(
                flight_no=flight_no,
                scheduled_departure=dep_time,
                scheduled_arrival=arrival_after(dep_time, dep, arr),
                fuel_infra_fee=random.choice((50, 60, 70, 90)),
                dep_airport_code=dep,
                dep_terminal=random.choice(TERMINALS),
                arr_airport_code=arr,
                arr_terminal=random.choice(TERMINALS),
                airline_code=airline,
                aircraft_model=choose_aircraft(dep, arr, aircraft_models),
                weekdays=choose_weekdays(),
                stopovers=stopovers,
                crawled=False,
            )
        )
    return generated


def write_base_csvs(airports: dict[str, Airport], aircraft_types: dict[str, AircraftType], output_dir: Path) -> None:
    with (output_dir / "airports.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["iata_code", "airport_name", "city_name"])
        for airport in airports.values():
            writer.writerow([airport.code, airport.name, airport.city])

    with (output_dir / "aircraft_types.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["model", "economy_seats", "first_seats"])
        for aircraft in aircraft_types.values():
            writer.writerow([aircraft.model, aircraft.economy_seats, aircraft.first_seats])


def write_csvs(flights: list[Flight], output_dir: Path) -> None:
    with (output_dir / "flights.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                "flight_no",
                "scheduled_departure",
                "scheduled_arrival",
                "fuel_infra_fee",
                "dep_airport_code",
                "dep_terminal",
                "arr_airport_code",
                "arr_terminal",
                "airline_code",
                "aircraft_model",
            ]
        )
        for flight in flights:
            writer.writerow(
                [
                    flight.flight_no,
                    flight.scheduled_departure,
                    flight.scheduled_arrival,
                    flight.fuel_infra_fee,
                    flight.dep_airport_code,
                    flight.dep_terminal,
                    flight.arr_airport_code,
                    flight.arr_terminal,
                    flight.airline_code,
                    flight.aircraft_model,
                ]
            )

    with (output_dir / "flight_weekdays.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["flight_no", "weekday"])
        for flight in flights:
            for weekday in sorted(flight.weekdays or []):
                writer.writerow([flight.flight_no, weekday])

    with (output_dir / "flight_stopovers.csv").open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["flight_no", "stop_order", "airport_code"])
        for flight in flights:
            for idx, airport_code in enumerate(flight.stopovers or [], start=1):
                writer.writerow([flight.flight_no, idx, airport_code])


def write_summary(flights: list[Flight], output_dir: Path) -> None:
    crawled = sum(1 for item in flights if item.crawled)
    summary = {
        "total_flights": len(flights),
        "crawled_flights": crawled,
        "completed_or_generated_flights": len(flights) - crawled,
        "airlines": sorted(AIRLINES),
    }
    (output_dir / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")


def walk_dicts(value: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(value, dict):
        found.append(value)
        for child in value.values():
            found.extend(walk_dicts(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(walk_dicts(child))
    return found


def first_value(row: dict[str, Any], *keys: str) -> str:
    lowered = {str(k).lower(): v for k, v in row.items()}
    for key in keys:
        value = row.get(key)
        if value is None:
            value = lowered.get(key.lower())
        if value not in (None, ""):
            return str(value).strip()
    return ""


def normalize_flight_no(value: str) -> str:
    match = re.search(r"\b(MU|FM)\s?(\d{3,4})\b", value.upper())
    return f"{match.group(1)}{match.group(2)}" if match else ""


def normalize_airport_code(value: str) -> str:
    value = value.upper().strip()
    return value if re.fullmatch(r"[A-Z]{3}", value) else ""


def normalize_time(value: str) -> str | None:
    match = re.search(r"(\d{1,2}):(\d{2})", value)
    if not match:
        return None
    hour = int(match.group(1)) % 24
    minute = int(match.group(2))
    return f"{hour:02d}:{minute:02d}:00"


def normalize_terminal(value: str) -> str | None:
    value = value.upper().strip()
    match = re.search(r"T\d[A-Z]?", value)
    return match.group(0)[:8] if match else None


def normalize_aircraft(value: str) -> str | None:
    compact = value.upper().replace("-", "").replace(" ", "")
    aliases = {
        "320": "A320",
        "321": "A321",
        "319": "A319",
        "332": "A332",
        "333": "A333",
        "359": "A359",
        "738": "B738",
        "789": "B789",
        "919": "C919",
    }
    for key, model in aliases.items():
        if key in compact or model in compact:
            return model
    if "ARJ" in compact:
        return "ARJ21"
    return None


def extract_stopovers(obj: dict[str, Any]) -> list[str]:
    raw = first_value(obj, "stopAirportCode", "stopoverAirportCode", "stopCode")
    codes = re.findall(r"[A-Z]{3}", raw.upper())
    return codes[:2]


def unique_flight_no(flight_no: str, used: set[str]) -> str:
    if flight_no not in used:
        return flight_no
    airline = flight_no[:2] if flight_no[:2] in AIRLINES else random.choice(tuple(AIRLINES))
    return make_flight_no(airline, used)


def make_flight_no(airline: str, used: set[str]) -> str:
    for _ in range(10000):
        number = random.randint(1000, 9999)
        flight_no = f"{airline}{number}"
        if flight_no not in used:
            return flight_no
    raise RuntimeError("unable to allocate unique flight number")


def random_time() -> str:
    hour = random.randint(6, 23)
    minute = random.choice((0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55))
    return f"{hour:02d}:{minute:02d}:00"


def arrival_after(dep_time: str, dep: str, arr: str) -> str:
    dep_dt = datetime.strptime(dep_time, "%H:%M:%S")
    duration = guessed_duration_minutes(dep, arr)
    arr_dt = dep_dt + timedelta(minutes=duration)
    return arr_dt.strftime("%H:%M:%S")


def guessed_duration_minutes(dep: str, arr: str) -> int:
    if dep[:1] == arr[:1]:
        return random.randint(65, 130)
    return random.randint(100, 310)


def choose_aircraft(dep: str, arr: str, aircraft_models: list[str]) -> str:
    available = aircraft_models or list(AIRCRAFT_MODELS)
    wide = [model for model in available if model in WIDE_BODY]
    narrow = [model for model in available if model in NARROW_BODY]
    if {dep, arr} & {"PVG", "SHA"} and wide and random.random() < 0.2:
        return random.choice(wide)
    if wide and random.random() < 0.12:
        return random.choice(wide)
    return random.choice(narrow or available)


def choose_weekdays() -> set[int]:
    mode = random.random()
    if mode < 0.58:
        return set(range(1, 8))
    if mode < 0.78:
        return {1, 3, 5, 7}
    if mode < 0.94:
        return {2, 4, 6}
    return set(random.sample(range(1, 8), random.randint(2, 5)))


def choose_stopovers(dep: str, arr: str, airports: list[str]) -> list[str]:
    candidates = [code for code in airports if code not in {dep, arr}]
    return random.sample(candidates, k=1) if candidates else []


if __name__ == "__main__":
    main()
