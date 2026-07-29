"""Web search using DuckDuckGo (no API key needed)."""

from duckduckgo_search import DDGS


def web_search(query: str, max_results: int = 5) -> str:
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        if not results:
            return "لم يتم العثور على نتائج."

        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "")
            body = r.get("body", "")
            href = r.get("href", "")
            lines.append(f"{i}. **{title}**\n{body}\n🔗 {href}")
        return "\n\n".join(lines)
    except Exception as e:
        return f"خطأ في البحث: {str(e)}"
