# This import will now work when run with pytest
from tools.web_search import web_search

def test_web_search_successful():
    """
    Tests if the web_search tool returns a successful result for a valid query.
    """
    print("🧪 Testing the web_search tool...")
    
    query = "آخرین وضعیت ویزای توریستی ایران برای شهروندان آلمان"
    result = web_search(query)
    
    print(f"\n--- Search Result for '{query}' ---")
    print(result)
    print("---------------------------------")
    
    # Pytest Assertion:
    # The test passes if the word "Error" is NOT in the result string.
    assert "Error" not in result
    assert "Summary Answer" in result

def test_web_search_no_api_key():
    """
    (Optional) A good test to ensure your error handling works.
    This test requires you to temporarily rename your TAVILY_API_KEY in the .env file.
    """
    # This test is commented out by default.
    # from config.settings import tavily_cfg
    # tavily_cfg.API_KEY = "" # Temporarily unset the key for this test
    # query = "test"
    # result = web_search(query)
    # assert "Error: Tavily API key is not configured" in result
    pass