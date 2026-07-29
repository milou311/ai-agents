from aaos.tools.registry import ToolRegistry


def test_register_and_specs():
    reg = ToolRegistry()

    def hello(args, ctx):
        return f"hi {args.get('name', '')}"

    reg.register(
        "hello",
        hello,
        "Say hi",
        {
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
        },
    )
    specs = reg.list_specs()
    assert len(specs) == 1
    assert specs[0]["function"]["name"] == "hello"
    assert reg.has("hello")


async def _run_async():
    reg = ToolRegistry()

    async def add(args, ctx):
        return str(int(args.get("a", 0)) + int(args.get("b", 0)))

    reg.register(
        "add",
        add,
        "Add two numbers",
        {"type": "object", "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}}},
    )
    out = await reg.run("add", {"a": 2, "b": 3}, {})
    assert out == "5"
    missing = await reg.run("nope", {}, {})
    assert "غير معروفة" in missing


def test_async_run():
    import asyncio

    asyncio.get_event_loop().run_until_complete(_run_async())
