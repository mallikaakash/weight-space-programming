#!/usr/bin/env python3
from score import extract_json_object, score_example


def test_extract_plain():
    assert extract_json_object('{"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}')["tool"] == "get_weather"


def test_extract_fence():
    text = 'Here:\n```json\n{"tool":"x","arguments":{}}\n```\n'
    assert extract_json_object(text)["tool"] == "x"


def test_strict_ok():
    expected = {"tool": "get_weather", "arguments": {"city": "Paris", "unit": "c"}}
    completion = '{"tool":"get_weather","arguments":{"city":"Paris","unit":"c"}}'
    s = score_example(expected, completion)
    assert s["strict_ok"]


def test_wrong_tool():
    expected = {"tool": "get_weather", "arguments": {"city": "Paris", "unit": "c"}}
    completion = '{"tool":"send_email","arguments":{"city":"Paris","unit":"c"}}'
    s = score_example(expected, completion)
    assert s["parse_ok"] and not s["tool_ok"] and not s["strict_ok"]


def test_extra_key_rejected():
    expected = {"tool": "get_weather", "arguments": {"city": "Paris", "unit": "c"}}
    completion = '{"tool":"get_weather","arguments":{"city":"Paris","unit":"c","country":"FR"}}'
    s = score_example(expected, completion)
    assert s["required_keys"] and not s["no_hallucinated_keys"] and not s["strict_ok"]


def test_exact_args_pass():
    expected = {"tool": "get_weather", "arguments": {"city": "Paris", "unit": "c"}}
    completion = '{"tool":"get_weather","arguments":{"unit":"c","city":"Paris"}}'
    s = score_example(expected, completion)
    assert s["no_hallucinated_keys"] and s["strict_ok"]


if __name__ == "__main__":
    test_extract_plain()
    test_extract_fence()
    test_strict_ok()
    test_wrong_tool()
    test_extra_key_rejected()
    test_exact_args_pass()
    print("ok")
