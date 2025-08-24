import asyncio
from autogen_agentchat.messages import TextMessage
from teams.travel_team import build_travel_team
import logging


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


    except Exception as e:
        print(f"\n❌ A critical error occurred: {e}")


if __name__ == "__main__": 
    asyncio.run(main())
