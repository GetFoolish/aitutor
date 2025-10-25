from google.adk.agents import Agent
import json 
import asyncio
from google.adk.runners import Runner
from google.genai import types
from google.adk.memory import InMemoryMemoryService
from google.adk.artifacts import InMemoryArtifactService
from google.adk.sessions import InMemorySessionService
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
from dotenv import load_dotenv 
from GenAIQuestions.agents.prompts.instructions import generator_instruction
from pathlib import Path

USER_ID="sherlockED"

questions_generator_agent = Agent(
    name="questions_generator_agent",
    description="Agent that generates new perseus format questions",
    model="gemini-2.0-flash",
    instruction=generator_instruction,
    output_key="question_json"
)

runner = Runner(
    app_name="QuestionsGenerator",
    agent=questions_generator_agent,
    session_service=InMemorySessionService(),
    artifact_service=InMemoryArtifactService(),
    memory_service=InMemoryMemoryService()
)

session_service = runner.session_service

async def create_session():
    session = await session_service.create_session(
        app_name="QuestionsGenerator",
        user_id=USER_ID
    )
    return session.id

SESSION_ID = asyncio.run(create_session()) 

async def execute(prompt: str) -> str:
    msg = prompt
    final_response = None
    
    async for ev in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=types.Content(
            role="user",
            parts=[types.Part(text=msg)]
        )):
        
        if hasattr(ev, 'content') and ev.content and ev.content.parts:
            response_text = ev.content.parts[0].text
            if ev.is_final_response():
                final_response = response_text
                
        # Check for tool-related events
        if hasattr(ev, 'tool_calls') and ev.tool_calls:
            print(f"TOOL CALLS: {ev.tool_calls}")
    
    return final_response
