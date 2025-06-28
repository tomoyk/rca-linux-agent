import asyncio

from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.auth.credential_service.in_memory_credential_service import (
    InMemoryCredentialService,
)
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types

from rca_agent.agent import root_agent


async def main():
    artifact_service = InMemoryArtifactService()
    session_service = InMemorySessionService()
    credential_service = InMemoryCredentialService()

    runner = Runner(
        app_name="rca_linux_agent",
        agent=root_agent,
        artifact_service=artifact_service,
        session_service=session_service,
        credential_service=credential_service,
    )

    session = await session_service.create_session(
        app_name="rca_linux_agent", user_id="user"
    )

    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text="collect")]),
    ):
        if event.content and event.content.parts:
            print(event.content.parts[0].text)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
