from aaos.models.gateway import _is_rate_limit, _is_tool_use_failed, _parse_xml_tool_call


class _Fake429(Exception):
    status_code = 429


class _FakeToolFail(Exception):
    status_code = 400

    def __str__(self):
        return 'Error code: 400 - tool_use_failed <function=manage_notes{"action":"get","key":"x"}</function>'


def test_rate_limit_detection():
    assert _is_rate_limit(_Fake429())


def test_tool_use_failed_detection():
    assert _is_tool_use_failed(_FakeToolFail())


def test_parse_xml_tool_call():
    text = '<function=manage_notes{"action":"get","key":"units_in_system"}</function>'
    parsed = _parse_xml_tool_call(text)
    assert parsed is not None
    name, args = parsed
    assert name == "manage_notes"
    assert args["action"] == "get"
    assert args["key"] == "units_in_system"
