from aaos.cognition.reflection import _extract_json
from aaos.cognition.tot import _extract_list


def test_extract_json():
    assert _extract_json('{"score": 0.9, "ok": true}')["score"] == 0.9


def test_extract_list():
    raw = '[{"id":"p1","summary":"A","steps":["1"],"score":0.8}]'
    assert _extract_list(raw)[0]["id"] == "p1"
