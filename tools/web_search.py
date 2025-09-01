from tavily import TavilyClient
from config.settings import tavily_cfg
import logging
from typing import Any, Dict, List

def web_search(query: str) -> Dict[str, Any]:
    """
    Performs a web search using the Tavily API and returns a summarized result.

    Args:
        query: The search query.

    Returns:
        {
          "ok": bool,
          "answer": str,
          "sources": [{"name": str, "url": str}]
        }
    """
    if not tavily_cfg.API_KEY:
        return {"ok": False, "answer": "", "sources": [], "error": "Tavily API key is not configured"}

    try:
        tavily = TavilyClient(api_key=tavily_cfg.API_KEY)
        resp = tavily.search(query=query, search_depth="basic", include_answer=True)
        answer = resp.get("answer", "") or ""
        results: List[Dict[str, str]] = resp.get("results", []) or []
        sources = []
        for r in results[:5]:
            name = r.get("title") or r.get("url") or "source"
            url = r.get("url") or ""
            if url:
                sources.append({"name": name, "url": url})
        return {"ok": True, "answer": answer, "sources": sources}
    except Exception as e:
        logging.error(f"An error occurred during Tavily web search: {e}")
        return {"ok": False, "answer": "", "sources": [], "error": str(e)}
