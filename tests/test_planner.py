from aaos.planner import Planner


def test_passthrough_simple():
    p = Planner()
    plan = p.plan("ما لون السماء؟")
    assert plan.passthrough is True


def test_search_plan():
    p = Planner()
    plan = p.plan("ابحث عن آخر أخبار الذكاء الاصطناعي")
    assert plan.passthrough is False
    tools = [s.tool for s in plan.steps if s.tool]
    assert "web_search" in tools


def test_knowledge_plan():
    p = Planner()
    plan = p.plan("ابحث في المعرفة عن سياسة الشركة")
    tools = [s.tool for s in plan.steps if s.tool]
    assert "knowledge_search" in tools
