from app.utils.khan_questions_loader import load_questions
from app.database.models import QuestionDocument

async def seed_db():
    questions = load_questions()
    if questions:
        for question in questions:
            question_data = QuestionDocument(
                **question
            )
            await question_data.insert()
        print("Database seeding successful")