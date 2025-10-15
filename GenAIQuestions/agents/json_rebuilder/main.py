from .agent import execute 

async def run(prompt: str):
    return await execute(prompt)