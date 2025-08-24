from autogen_agentchat.messages import TextMessage
from teams.travel_team import build_travel_team
import logging
import asyncio
import openai


logging.basicConfig(level=logging.INFO)


async def main():
    try:
        print("🚀 Building the agent team...")
        team = await build_travel_team()
        print("✅ Team successfully built.")


        task = TextMessage(
            content="یک برنامه سفر به مشهد بهم بده؛ من در تاریخ یک شهریور 1404 می‌رم مشهد",
            source="user"
        )
        
        print("⏳ Running task by the team...")
        result = await team.run(task=task)
        print("✅ Task completed.")


        if result and result.messages:
            for message in result.messages:
                print(f"--- Message from {message.source} ---")
                print(message.content)
                print("---------------------------------\n")
        else:
            print("⚠️ No result received from team execution.")


    # ----- Specific API Error Handling -----
    except openai.AuthenticationError as e:
        print("\n❌ Authentication Error: Your API key is invalid or expired.")
        print(f"   Details: {e}")
    except openai.RateLimitError as e:
        print("\n❌ Rate Limit Error: You have exceeded the API request limit. Please wait and try again later.")
        print(f"   Details: {e}")
    except openai.APITimeoutError as e:
        print("\n❌ API Timeout Error: The request to the API timed out. Please try again.")
        print(f"   Details: {e}")
    except openai.APIConnectionError as e:
        print("\n❌ API Connection Error: Could not connect to the API server. Check your internet connection.")
        print(f"   Details: {e}")
    except Exception as e:
        print(f"\n❌ An unexpected error occurred: {e}")


if __name__ == "__main__": 
    asyncio.run(main())
