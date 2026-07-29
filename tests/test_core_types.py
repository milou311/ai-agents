from aaos.core.types import AgentRequest, AgentResponse


def test_agent_request_defaults():
    r = AgentRequest(
        request_id="1",
        user_id="42",
        channel="telegram",
        text="مرحبا",
    )
    assert r.attachments == []
    assert r.metadata == {}


def test_agent_response():
    resp = AgentResponse(request_id="1", text="أهلاً")
    assert resp.error is None
    assert resp.tool_traces == []
