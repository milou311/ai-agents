from aaos.cognition.a2a import A2ABus


def test_send_receive():
    bus = A2ABus()
    bus.send("research", "ops", {"partial": "found 3 sources"})
    msgs = bus.receive("ops")
    assert len(msgs) == 1
    assert msgs[0].payload["partial"] == "found 3 sources"


def test_broadcast():
    bus = A2ABus()
    bus.publish("supervisor", "broadcast:assignment", {"agent": "research"})
    hist = bus.history("broadcast:assignment")
    assert len(hist) == 1
