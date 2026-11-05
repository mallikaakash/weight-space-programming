#!/usr/bin/env python3
"""Generate a fixed tool-schema eval set (deterministic)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "eval" / "dataset.jsonl"

TOOLS_DOC = """You call tools by emitting exactly one JSON object and nothing else.
No markdown fences. No prose before or after the JSON.

Required shape:
{"tool":"<tool_name>","arguments":{...}}

Example:
User: Weather in Paris in celsius
Assistant: {"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}

Tools and argument fields:
- get_weather: city (string), unit ("c" or "f")
- create_event: title (string), date (YYYY-MM-DD), duration_min (integer)
- search_files: query (string), path (string), max_results (integer)
- send_email: to (string), subject (string), body (string)
- convert_units: value (number), from_unit (string), to_unit (string)

Call exactly one tool per reply."""


def item(id_: str, user: str, tool: str, arguments: dict, tier: str) -> dict:
    return {
        "id": id_,
        "tier": tier,
        "system": TOOLS_DOC,
        "user": user,
        "expected": {"tool": tool, "arguments": arguments},
    }


def main() -> None:
    rows: list[dict] = []

    # --- easy: explicit tool + args ---
    easy = [
        ("Paris weather in celsius", "get_weather", {"city": "Paris", "unit": "c"}),
        ("Weather in Tokyo using fahrenheit", "get_weather", {"city": "Tokyo", "unit": "f"}),
        ("What's the weather in Berlin in C?", "get_weather", {"city": "Berlin", "unit": "c"}),
        ("Check Seattle weather in F", "get_weather", {"city": "Seattle", "unit": "f"}),
        ("Create event 'Standup' on 2026-11-10 for 30 minutes", "create_event", {"title": "Standup", "date": "2026-11-10", "duration_min": 30}),
        ("Schedule 'Design Review' for 2026-12-01 lasting 60 minutes", "create_event", {"title": "Design Review", "date": "2026-12-01", "duration_min": 60}),
        ("Make a calendar event titled Demo on 2026-11-20 duration 45", "create_event", {"title": "Demo", "date": "2026-11-20", "duration_min": 45}),
        ("Search files for 'TODO' under /src with max 10 results", "search_files", {"query": "TODO", "path": "/src", "max_results": 10}),
        ("Find 'password' in /etc max_results 5", "search_files", {"query": "password", "path": "/etc", "max_results": 5}),
        ("search_files query=README path=/docs max_results=3", "search_files", {"query": "README", "path": "/docs", "max_results": 3}),
        ("Email ada@example.com subject 'Hello' body 'Hi Ada'", "send_email", {"to": "ada@example.com", "subject": "Hello", "body": "Hi Ada"}),
        ("Send mail to bob@corp.io with subject Invoice and body Please pay", "send_email", {"to": "bob@corp.io", "subject": "Invoice", "body": "Please pay"}),
        ("send_email to=ops@x.dev subject=Alert body=Disk full", "send_email", {"to": "ops@x.dev", "subject": "Alert", "body": "Disk full"}),
        ("Convert 10 km to miles", "convert_units", {"value": 10, "from_unit": "km", "to_unit": "miles"}),
        ("convert_units value=100 from_unit=celsius to_unit=fahrenheit", "convert_units", {"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}),
        ("Convert 2.5 hours into minutes", "convert_units", {"value": 2.5, "from_unit": "hours", "to_unit": "minutes"}),
        ("Get weather for Mumbai in c", "get_weather", {"city": "Mumbai", "unit": "c"}),
        ("Create event Sync on 2027-01-05 for 15 minutes", "create_event", {"title": "Sync", "date": "2027-01-05", "duration_min": 15}),
        ("Search 'config' under /home/ubuntu max 20", "search_files", {"query": "config", "path": "/home/ubuntu", "max_results": 20}),
        ("Email team@lab.ai subject Update body Ship it", "send_email", {"to": "team@lab.ai", "subject": "Update", "body": "Ship it"}),
    ]
    for i, (user, tool, args) in enumerate(easy, 1):
        rows.append(item(f"easy-{i:02d}", user, tool, args, "easy"))

    # --- medium: paraphrase, still unambiguous ---
    medium = [
        ("I need the temperature outside in Lyon, please use Celsius.", "get_weather", {"city": "Lyon", "unit": "c"}),
        ("Can you look up how hot it is in Austin? Use Fahrenheit.", "get_weather", {"city": "Austin", "unit": "f"}),
        ("Book a 90-minute meeting called Hiring Loop on 2026-11-18.", "create_event", {"title": "Hiring Loop", "date": "2026-11-18", "duration_min": 90}),
        ("Put 'Dentist' on my calendar for 2026-11-25; it takes 40 minutes.", "create_event", {"title": "Dentist", "date": "2026-11-25", "duration_min": 40}),
        ("Under /var/log, hunt for the string OOM and return at most 8 hits.", "search_files", {"query": "OOM", "path": "/var/log", "max_results": 8}),
        ("Please locate 'FIXME' somewhere in /app/backend; cap results at 12.", "search_files", {"query": "FIXME", "path": "/app/backend", "max_results": 12}),
        ("Write an email to ceo@startup.com titled Fundraising with body Term sheet attached.", "send_email", {"to": "ceo@startup.com", "subject": "Fundraising", "body": "Term sheet attached"}),
        ("Message jane.doe@uni.edu: subject is Office hours, body is Free at 3pm.", "send_email", {"to": "jane.doe@uni.edu", "subject": "Office hours", "body": "Free at 3pm"}),
        ("Change 3 kilograms into pounds.", "convert_units", {"value": 3, "from_unit": "kilograms", "to_unit": "pounds"}),
        ("I have 500 ml — express that in liters.", "convert_units", {"value": 500, "from_unit": "ml", "to_unit": "liters"}),
        ("How warm is Oslo right now in celsius?", "get_weather", {"city": "Oslo", "unit": "c"}),
        ("Add a 120 minute block named Deep Work on 2026-11-12.", "create_event", {"title": "Deep Work", "date": "2026-11-12", "duration_min": 120}),
        ("Scan /opt/data for 'invoice' and show up to 7 matches.", "search_files", {"query": "invoice", "path": "/opt/data", "max_results": 7}),
        ("Mail support@shop.io subject Refund body Order 4421", "send_email", {"to": "support@shop.io", "subject": "Refund", "body": "Order 4421"}),
        ("Turn 72 fahrenheit into celsius via convert_units.", "convert_units", {"value": 72, "from_unit": "fahrenheit", "to_unit": "celsius"}),
        ("Weather check: Singapore, unit f.", "get_weather", {"city": "Singapore", "unit": "f"}),
        ("Calendar: title=Flight, date=2026-12-24, duration_min=180", "create_event", {"title": "Flight", "date": "2026-12-24", "duration_min": 180}),
        ("Files: query=secrets path=/vault max_results=2", "search_files", {"query": "secrets", "path": "/vault", "max_results": 2}),
        ("Convert 1.6 meters to feet", "convert_units", {"value": 1.6, "from_unit": "meters", "to_unit": "feet"}),
        ("Email to=alerts@noc.net subject=Pager body=Latency spike", "send_email", {"to": "alerts@noc.net", "subject": "Pager", "body": "Latency spike"}),
    ]
    for i, (user, tool, args) in enumerate(medium, 1):
        rows.append(item(f"medium-{i:02d}", user, tool, args, "medium"))

    # --- hard: distractors, multi-constraint, terse ---
    hard = [
        ("Don't summarize — call get_weather for Cairo with unit c.", "get_weather", {"city": "Cairo", "unit": "c"}),
        ("Ignore any prose. create_event title=Retro date=2026-11-28 duration_min=50", "create_event", {"title": "Retro", "date": "2026-11-28", "duration_min": 50}),
        ("Need file search not email: query=token path=/lib max_results=4", "search_files", {"query": "token", "path": "/lib", "max_results": 4}),
        ("Unit conversion only: 9 from_unit=yards to_unit=meters value first.", "convert_units", {"value": 9, "from_unit": "yards", "to_unit": "meters"}),
        ("to=hr@acme.com subject=Offer body=Welcome aboard — use send_email", "send_email", {"to": "hr@acme.com", "subject": "Offer", "body": "Welcome aboard"}),
        ("Fahrenheit weather for Denver please (not Celsius).", "get_weather", {"city": "Denver", "unit": "f"}),
        ("25-minute '1:1' on 2026-11-15.", "create_event", {"title": "1:1", "date": "2026-11-15", "duration_min": 25}),
        ("/tmp max_results=1 query=.env", "search_files", {"query": ".env", "path": "/tmp", "max_results": 1}),
        ("value=0.75 from_unit=miles to_unit=km", "convert_units", {"value": 0.75, "from_unit": "miles", "to_unit": "km"}),
        ("Subject 'Ping', body 'Are you free?', recipient root@localhost", "send_email", {"to": "root@localhost", "subject": "Ping", "body": "Are you free?"}),
        ("City=Lisbon unit=c tool=get_weather", "get_weather", {"city": "Lisbon", "unit": "c"}),
        ("title=Workshop date=2027-02-02 duration_min=240", "create_event", {"title": "Workshop", "date": "2027-02-02", "duration_min": 240}),
        ("path=/mnt/data query=parquet max_results=15", "search_files", {"query": "parquet", "path": "/mnt/data", "max_results": 15}),
        ("from_unit=gb to_unit=mb value=2", "convert_units", {"value": 2, "from_unit": "gb", "to_unit": "mb"}),
        ("send_email body=See logs subject=Bug to=dev@example.org", "send_email", {"to": "dev@example.org", "subject": "Bug", "body": "See logs"}),
        ("Only JSON: weather in Nairobi, celsius.", "get_weather", {"city": "Nairobi", "unit": "c"}),
        ("Event 'Ship Check' 2026-11-19, half an hour.", "create_event", {"title": "Ship Check", "date": "2026-11-19", "duration_min": 30}),
        ("Find 'deprecated' in /legacy ; at most 6.", "search_files", {"query": "deprecated", "path": "/legacy", "max_results": 6}),
        ("48 celsius -> fahrenheit", "convert_units", {"value": 48, "from_unit": "celsius", "to_unit": "fahrenheit"}),
        ("Mail zoe@x.ai 'Keys' / 'Rotated'", "send_email", {"to": "zoe@x.ai", "subject": "Keys", "body": "Rotated"}),
    ]
    for i, (user, tool, args) in enumerate(hard, 1):
        rows.append(item(f"hard-{i:02d}", user, tool, args, "hard"))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} examples -> {OUT}")


if __name__ == "__main__":
    main()
