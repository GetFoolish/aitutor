"""
Quick script to check database status
Run this to see if you have questions in the database
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from pathlib import Path
import sys

# Add parent directory to path to import models
sys.path.insert(0, str(Path(__file__).parent / "SherlockEDApi"))

from app.database.models import QuestionDocument, GeneratedQuestionDocument

async def check_database():
    print("Connecting to MongoDB...")
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["question_db"]
    
    await init_beanie(database=db, document_models=[QuestionDocument, GeneratedQuestionDocument])
    
    print("\n" + "="*50)
    print("DATABASE STATUS")
    print("="*50)
    
    # Count total questions
    total_questions = await QuestionDocument.find().count()
    print(f"\n📊 Total Questions: {total_questions}")
    
    # Count questions with generated items
    questions_with_generated = await QuestionDocument.find(
        QuestionDocument.generated_count > 0
    ).count()
    print(f"📝 Questions with Generated Items: {questions_with_generated}")
    
    # Count questions pending approval
    all_questions = await QuestionDocument.find(
        QuestionDocument.generated_count > 0
    ).to_list()
    
    pending_count = 0
    for q in all_questions:
        await q.fetch_all_links()
        for gen_q in q.generated:
            await gen_q.fetch()
            if not gen_q.human_approved:
                pending_count += 1
                break
    
    print(f"⏳ Questions Pending Approval: {pending_count}")
    
    # Show sample question IDs
    if total_questions > 0:
        print(f"\n📋 Sample Question IDs:")
        sample = await QuestionDocument.find().limit(5).to_list()
        for q in sample:
            print(f"   - {q.id} (generated_count: {q.generated_count})")
    
    print("\n" + "="*50)
    
    if total_questions == 0:
        print("\n⚠️  Database is empty!")
        print("   The backend should auto-seed when started.")
        print("   Make sure 'SherlockEDApi/CurriculumBuilder' folder has JSON files.")
    elif questions_with_generated == 0:
        print("\n⚠️  No questions have been generated yet!")
        print("   Run 'python GenAIQuestions/generate_questions.py' to generate some.")
    elif pending_count == 0:
        print("\n✅ All generated questions have been approved!")
    else:
        print(f"\n✅ You have {pending_count} question(s) pending approval!")
    
    client.close()

if __name__ == "__main__":
    asyncio.run(check_database())

