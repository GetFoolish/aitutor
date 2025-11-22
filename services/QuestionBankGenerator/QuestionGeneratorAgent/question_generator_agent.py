import json
import time
import re
import sys
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from LLMBase.llm_client import OpenRouterClient
from .validators import SubjectValidator

# Determine project root to reliably find config.json
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(PROJECT_ROOT, 'config.json')

class QuestionGeneratorAgent:
    def __init__(self, curriculum_file: str):
        if not os.path.isabs(curriculum_file):
            raise ValueError("QuestionGeneratorAgent requires an absolute path for the curriculum_file.")
        self.curriculum_file = curriculum_file
        self.llm_client = OpenRouterClient(config_path=CONFIG_PATH)
        self.validator = SubjectValidator()
        self.load_curriculum()
        
    def load_curriculum(self):
        """Load the current curriculum"""
        with open(self.curriculum_file, 'r') as f:
            self.curriculum = json.load(f)
    
    def save_curriculum(self):
        """Save the updated curriculum"""
        with open(self.curriculum_file, 'w') as f:
            json.dump(self.curriculum, f, indent=2)
    
    def generate_variations(self, source_question_id: str, num_variations: int = 3, 
                          subject: str = "math") -> List[str]:
        """Generate variations of a question"""
        
        # Find the source question
        source_question = self._find_question(source_question_id)
        if not source_question:
            raise ValueError(f"Question {source_question_id} not found")
        
        # Extract relevant info
        skill_id = self._get_skill_id_for_question(source_question_id)
        grade_level = self._get_grade_for_skill(skill_id)
        
        # Generate variations
        generated_ids = []
        
        for i in range(num_variations):
            try:
                variation = self._generate_single_variation(
                    source_question, skill_id, grade_level, i + 1, subject
                )
                if variation:
                    generated_ids.append(variation['question_id'])
            except Exception as e:
                print(f"Error generating variation {i+1}: {e}")
        
        # Save updated curriculum
        self.save_curriculum()
        
        return generated_ids
    
    def _generate_single_variation(self, source_question: Dict, skill_id: str, 
                                 grade_level: str, variation_num: int, 
                                 subject: str) -> Optional[Dict]:
        """Generate a single question variation"""
        
        # Create prompt for LLM
        system_prompt = f"""You are an expert educational content creator specializing in {subject}.
Your task is to create variations of educational questions while maintaining the same difficulty level and learning objective."""
        
        if subject == "math":
            user_prompt = f"""Create a variation of this math question:
Original Question: {source_question['content']}
Original Answer: {source_question['correct_answer']}
Grade Level: {grade_level}
Difficulty: {source_question['difficulty']}

Requirements:
1. Keep the same mathematical concept and operation
2. Use different numbers (avoid using the same numbers)
3. Maintain similar difficulty (±0.1)
4. Optionally change the context/story while keeping the math the same
5. Ensure the problem has a clear, definite answer

Respond in JSON format:
{{
    "question": "the new question text",
    "answer": "the correct answer",
    "explanation": "brief explanation of what changed"
}}"""
        else:
            user_prompt = f"""Create a variation of this {subject} question:
Original Question: {source_question['content']}
Original Answer: {source_question['correct_answer']}
Grade Level: {grade_level}
Difficulty: {source_question['difficulty']}

Requirements:
1. Keep the same learning objective and concept
2. Ask about a related but different aspect
3. Maintain similar difficulty
4. Ensure factual accuracy
5. Provide sources if applicable

Respond in JSON format:
{{
    "question": "the new question text",
    "answer": "the correct answer",
    "explanation": "brief explanation of what changed",
    "sources": ["source1", "source2"] // optional, for fact-based questions
}}"""
        
        try:
            # Generate variation using LLM
            response = self.llm_client.generate(user_prompt, "question_generator", system_prompt)
            
            # Parse response
            variation_data = self._parse_llm_response(response)
            
            # Validate the generated question and answer
            sources = variation_data.get('sources', [])
            is_valid, validation_data = self.validator.validate(
                variation_data['question'], 
                variation_data['answer'], 
                subject,
                sources
            )
            
            if not is_valid:
                print(f"Validation failed: {validation_data}")
                return None
            
            # Create new question object
            new_question_id = f"{source_question['question_id']}_gen_{variation_num:03d}"
            
            new_question = {
                "question_id": new_question_id,
                "content": variation_data['question'],
                "difficulty": source_question['difficulty'],
                "expected_time_seconds": source_question['expected_time_seconds'],
                "correct_answer": variation_data['answer'],
                "metadata": {
                    "generated": True,
                    "source_question_id": source_question['question_id'],
                    "generated_at": datetime.now().isoformat(),
                    "subject": subject,
                    "explanation": variation_data.get('explanation', ''),
                    "model_used": self.llm_client.config_manager.get_llm_config("question_generator")["model"]
                }
            }
            
            # Add sources for fact-based questions
            if subject != "math" and sources:
                new_question["sources"] = sources
            
            # Check for duplicates
            if not self._is_duplicate(new_question):
                # Add to curriculum
                self._add_question_to_curriculum(new_question, skill_id, grade_level)
                print(f"✅ Generated: {new_question_id}")
                return new_question
            else:
                print(f"⚠️  Duplicate detected, skipping")
                return None
                
        except Exception as e:
            print(f"Error in generation: {e}")
            return None
    
    def _parse_llm_response(self, response: str) -> Dict:
        """Parse LLM response to extract question data"""
        try:
            # Try to extract JSON from response
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # Fallback: parse structured text
                lines = response.strip().split('\n')
                data = {}
                for line in lines:
                    if 'question:' in line.lower():
                        data['question'] = line.split(':', 1)[1].strip()
                    elif 'answer:' in line.lower():
                        data['answer'] = line.split(':', 1)[1].strip()
                    elif 'explanation:' in line.lower():
                        data['explanation'] = line.split(':', 1)[1].strip()
                
                if 'question' in data and 'answer' in data:
                    return data
                else:
                    raise ValueError("Could not parse question and answer from response")
                    
        except json.JSONDecodeError as e:
            raise ValueError(f"Failed to parse JSON response: {e}")
    
    def _is_duplicate(self, new_question: Dict) -> bool:
        """Check if question is too similar to existing ones"""
        new_content = new_question['content'].lower().strip()
        new_answer = str(new_question['correct_answer']).lower().strip()
        
        # Check all questions in curriculum
        for grade_data in self.curriculum['grades'].values():
            for skill_data in grade_data['skills']:
                for question in skill_data['questions']:
                    existing_content = question['content'].lower().strip()
                    existing_answer = str(question['correct_answer']).lower().strip()
                    
                    # Exact match
                    if new_content == existing_content:
                        return True
                    
                    # Very similar (only numbers different)
                    if self._are_questions_too_similar(new_content, existing_content):
                        # Check if answers are also the same
                        if new_answer == existing_answer:
                            return True
        
        return False
    
    def _are_questions_too_similar(self, q1: str, q2: str) -> bool:
        """Check if two questions are too similar (ignoring numbers)"""
        # Replace numbers with placeholder
        q1_normalized = re.sub(r'\d+', 'NUM', q1)
        q2_normalized = re.sub(r'\d+', 'NUM', q2)
        
        # Check similarity
        return q1_normalized == q2_normalized
    
    def _find_question(self, question_id: str) -> Optional[Dict]:
        """Find a question by ID in the curriculum"""
        for grade_data in self.curriculum['grades'].values():
            for skill_data in grade_data['skills']:
                for question in skill_data['questions']:
                    if question['question_id'] == question_id:
                        return question
        return None
    
    def _get_skill_id_for_question(self, question_id: str) -> Optional[str]:
        """Get the skill ID for a given question"""
        for grade_data in self.curriculum['grades'].values():
            for skill_data in grade_data['skills']:
                for question in skill_data['questions']:
                    if question['question_id'] == question_id:
                        return skill_data['skill_id']
        return None
    
    def _get_grade_for_skill(self, skill_id: str) -> Optional[str]:
        """Get the grade level for a skill"""
        for grade_key, grade_data in self.curriculum['grades'].items():
            for skill_data in grade_data['skills']:
                if skill_data['skill_id'] == skill_id:
                    return grade_key
        return None
    
    def _add_question_to_curriculum(self, question: Dict, skill_id: str, grade_level: str):
        """Add a new question to the curriculum"""
        # Find the right place to add the question
        if grade_level in self.curriculum['grades']:
            for skill_data in self.curriculum['grades'][grade_level]['skills']:
                if skill_data['skill_id'] == skill_id:
                    skill_data['questions'].append(question)
                    return
        
        raise ValueError(f"Could not find skill {skill_id} in grade {grade_level}")


# Test function
def test_generator():
    """Test the question generator"""
    print("🧪 Testing Question Generator Agent")
    print("=" * 50)
    
    try:
        # Initialize generator
        generator = QuestionGeneratorAgent()
        
        # Test with a simple math question
        print("\n📚 Generating variations for 'What is 2 + 3?'")
        generated_ids = generator.generate_variations("g1_add_1", num_variations=3)
        
        print(f"\n✨ Generated {len(generated_ids)} variations:")
        for qid in generated_ids:
            question = generator._find_question(qid)
            if question:
                print(f"  - {qid}: {question['content']} = {question['correct_answer']}")
        
        print("\n✅ Test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")


if __name__ == "__main__":
    test_generator()