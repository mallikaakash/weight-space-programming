# Failure spot-check

Source: `tool_schema_stability-r3_20261105T071937Z.json` (tag `stability-r3`, split `test`). 16/20 strict failures; showing 15.

## easy-06 (easy) — wrong tool
- user: Schedule 'Design Review' for 2026-12-01 lasting 60 minutes
- expected tool: `create_event` args `{"title": "Design Review", "date": "2026-12-01", "duration_min": 60}`
- completion: `{"tool":"schedule","arguments":{"date":"2026-12-01","duration":"60"}}`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## easy-15 (easy) — parse fail
- user: convert_units value=100 from_unit=celsius to_unit=fahrenheit
- expected tool: `convert_units` args `{"value": 100, "from_unit": "celsius", "to_unit": "fahrenheit"}`
- completion: `{"tool":"convert_units","arguments":{"value":100,"from_unit":"c","to_unit":"f"}`
- failed flags: parse_ok, tool_ok, args_is_object, required_keys, no_hallucinated_keys, types_ok, values_ok

## hard-14 (hard) — bad values
- user: from_unit=gb to_unit=mb value=2
- expected tool: `convert_units` args `{"value": 2, "from_unit": "gb", "to_unit": "mb"}`
- completion: `{"tool":"convert_units","arguments":{"from_unit":"mb","to_unit":"gb","value":2}}`
- failed flags: values_ok

## easy-09 (easy) — wrong tool
- user: Find 'password' in /etc max_results 5
- expected tool: `search_files` args `{"query": "password", "path": "/etc", "max_results": 5}`
- completion: `{"tool":"get_max_results","arguments":{"max_results":"5"}}`
- failed flags: tool_ok, required_keys, types_ok, values_ok

## medium-14 (medium) — parse fail
- user: Mail support@shop.io subject Refund body Order 4421
- expected tool: `send_email` args `{"to": "support@shop.io", "subject": "Refund", "body": "Order 4421"}`
- completion: `{"tool":"mail","arguments":{"subject":"Refund","body":"Order 4421"},"tool":"mail","arguments":{"subject":"Refund","body":"Order 4421"},"tool":"mail","arguments":{"subject":"Refund","body":"Order 44...`
- failed flags: parse_ok, tool_ok, args_is_object, required_keys, no_hallucinated_keys, types_ok, values_ok

## easy-12 (easy) — wrong tool
- user: Send mail to bob@corp.io with subject Invoice and body Please pay
- expected tool: `send_email` args `{"to": "bob@corp.io", "subject": "Invoice", "body": "Please pay"}`
- completion: `{"tool":"send_email","arguments":{"to":"bob@corp.io","subject":"Invoice","body":"Please pay"},"tool":"create_event","arguments":{"city":"Paris","unit":"c","title":"Invoice","date":"2023-01-01","dur...`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## medium-20 (medium) — parse fail
- user: Email to=alerts@noc.net subject=Pager body=Latency spike
- expected tool: `send_email` args `{"to": "alerts@noc.net", "subject": "Pager", "body": "Latency spike"}`
- completion: `{"tool":"send_email","arguments":{"to":"alerts@noc.net","subject":"Pager","body":"Latency spike"}`
- failed flags: parse_ok, tool_ok, args_is_object, required_keys, no_hallucinated_keys, types_ok, values_ok

## easy-18 (easy) — wrong tool
- user: Create event Sync on 2027-01-05 for 15 minutes
- expected tool: `create_event` args `{"title": "Sync", "date": "2027-01-05", "duration_min": 15}`
- completion: `{"tool":"sync","arguments":{"date":"2027-01-05","duration_min":15}}`
- failed flags: tool_ok, required_keys, types_ok, values_ok

## hard-05 (hard) — parse fail
- user: to=hr@acme.com subject=Offer body=Welcome aboard — use send_email
- expected tool: `send_email` args `{"to": "hr@acme.com", "subject": "Offer", "body": "Welcome aboard"}`
- completion: `{"tool":"send_email","arguments":{"to":"hr@acme.com","subject":"Offer","body":"Welcome aboard — use send_email"}`
- failed flags: parse_ok, tool_ok, args_is_object, required_keys, no_hallucinated_keys, types_ok, values_ok

## medium-02 (medium) — wrong tool
- user: Can you look up how hot it is in Austin? Use Fahrenheit.
- expected tool: `get_weather` args `{"city": "Austin", "unit": "f"}`
- completion: `{"tool":"get_temperature","arguments":{"city":"Austin","unit":"F"},"result":{"temperature":285.6}}`
- failed flags: tool_ok, values_ok

## medium-05 (medium) — wrong tool
- user: Under /var/log, hunt for the string OOM and return at most 8 hits.
- expected tool: `search_files` args `{"query": "OOM", "path": "/var/log", "max_results": 8}`
- completion: `{ "tool": "hunt", "arguments": { "path": "/var/log", "regex": "OOM" } }`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## medium-08 (medium) — wrong tool
- user: Message jane.doe@uni.edu: subject is Office hours, body is Free at 3pm.
- expected tool: `send_email` args `{"to": "jane.doe@uni.edu", "subject": "Office hours", "body": "Free at 3pm"}`
- completion: `{"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## medium-17 (medium) — wrong tool
- user: Calendar: title=Flight, date=2026-12-24, duration_min=180
- expected tool: `create_event` args `{"title": "Flight", "date": "2026-12-24", "duration_min": 180}`
- completion: `{"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## hard-08 (hard) — wrong tool
- user: /tmp max_results=1 query=.env
- expected tool: `search_files` args `{"query": ".env", "path": "/tmp", "max_results": 1}`
- completion: `{"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## hard-17 (hard) — wrong tool
- user: Event 'Ship Check' 2026-11-19, half an hour.
- expected tool: `create_event` args `{"title": "Ship Check", "date": "2026-11-19", "duration_min": 30}`
- completion: `{"tool":"ship_check","arguments":{"date":"2026-11-19","half_hour":"00:00:00"}}`
- failed flags: tool_ok, required_keys, no_hallucinated_keys, types_ok, values_ok

## Notes

- **wrong tool**: 11 of 16 failures
- **parse fail**: 4 of 16 failures
- **bad values**: 1 of 16 failures
