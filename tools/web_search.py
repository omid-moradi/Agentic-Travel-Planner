from tavily import TavilyClient
from config.settings import tavily_cfg
import logging

def web_search(query: str) -> str:
    """
    Performs a web search using the Tavily API and returns a summarized result.

    Args:
        query: The search query.

    Returns:
        A formatted string containing the search results, or an error message.
    """
    if not tavily_cfg.API_KEY:
        return "Error: Tavily API key is not configured. Cannot perform web search."

    try:
        # Initialize the Tavily client
        tavily = TavilyClient(api_key=tavily_cfg.API_KEY)

        # Perform the search. 'include_answer' provides a summarized answer.
        response = tavily.search(query=query, search_depth="basic", include_answer=True)

        # Format the results into a clean string
        answer = response.get("answer", "No summary answer found.")
        results = response.get("results", [])

        formatted_results = f"**Summary Answer:**\n{answer}\n\n**Sources:**\n"
        for result in results[:3]: # Return top 3 sources
            formatted_results += f"- Title: {result.get('title')}\n  URL: {result.get('url')}\n"

        return formatted_results

    except Exception as e:
        logging.error(f"An error occurred during Tavily web search: {e}")
        return f"Error performing web search: {e}"
    

query = "بهترین مهاجم تاریخ کیست؟"
result = web_search(query)
print(result)