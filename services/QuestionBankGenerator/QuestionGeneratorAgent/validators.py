import re
import json
from typing import Dict, Tuple, Optional, List
from abc import ABC, abstractmethod

class BaseValidator(ABC):
    @abstractmethod
    def validate(self, question: str, answer: str) -> Tuple[bool, str]:
        """Validate question and answer. Returns (is_valid, error_message)"""
        pass

class MathValidator(BaseValidator):
    def validate(self, question: str, answer: str) -> Tuple[bool, str]:
        """Validate mathematical questions and answers"""
        try:
            # Basic validation - answer should not be empty
            if not answer or not answer.strip():
                return False, "Answer cannot be empty"
            
            # Check if answer contains basic math operations that shouldn't be there
            if any(op in answer for op in ['=', '?']) and 'x =' not in answer:
                return False, "Answer contains invalid characters"
            
            # For equations, ensure they follow proper format
            if 'x =' in answer or 'y =' in answer:
                # Validate equation format
                if not re.match(r'^[xy]\s*=\s*-?\d+(\.\d+)?$', answer.strip()):
                    return False, "Invalid equation format"
            
            # For numeric answers, try to parse them
            if re.match(r'^-?\d+(\.\d+)?$', answer.strip()):
                try:
                    float(answer.strip())
                except ValueError:
                    return False, "Invalid numeric answer"
            
            # For fraction answers
            if '/' in answer:
                if not re.match(r'^-?\d+/\d+$', answer.strip()):
                    return False, "Invalid fraction format"
            
            return True, ""
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class FactBasedValidator(BaseValidator):
    def __init__(self):
        self.llm_client = None  # Will be initialized when needed
    
    def validate(self, question: str, answer: str, sources: List[str] = None) -> Tuple[bool, Dict]:
        """
        Validate fact-based questions (Science, History, Arts)
        Returns (is_valid, validation_data)
        """
        validation_data = {
            "is_valid": True,
            "error_message": "",
            "sources": sources or [],
            "confidence": 0.0,
            "fact_check_notes": ""
        }
        
        # Basic validation
        if not answer or not answer.strip():
            validation_data["is_valid"] = False
            validation_data["error_message"] = "Answer cannot be empty"
            return False, validation_data
        
        # Length check for fact-based answers
        if len(answer.strip()) < 3:
            validation_data["is_valid"] = False
            validation_data["error_message"] = "Answer too short for a fact-based question"
            return False, validation_data
        
        # If sources provided, ensure they're valid URLs or references
        if sources:
            for source in sources:
                if not self._is_valid_source(source):
                    validation_data["is_valid"] = False
                    validation_data["error_message"] = f"Invalid source: {source}"
                    return False, validation_data
        
        # For now, we'll trust the LLM's fact generation
        # In production, you'd want to fact-check against reliable sources
        validation_data["confidence"] = 0.9  # High confidence for LLM-generated content
        validation_data["fact_check_notes"] = "LLM-generated content, manual verification recommended"
        
        return True, validation_data
    
    def _is_valid_source(self, source: str) -> bool:
        """Check if a source is a valid URL or reference"""
        # URL pattern
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        # Book/Article reference pattern (basic)
        ref_pattern = re.compile(r'^[\w\s,.\-()]+,\s*\d{4}')  # "Author, Year" format
        
        return bool(url_pattern.match(source) or ref_pattern.match(source))

class SubjectValidator:
    """Main validator that routes to appropriate subject-specific validator"""
    
    def __init__(self):
        self.math_validator = MathValidator()
        self.fact_validator = FactBasedValidator()
    
    def validate(self, question: str, answer: str, subject: str = "math", 
                sources: List[str] = None) -> Tuple[bool, Dict]:
        """
        Validate based on subject
        Returns (is_valid, validation_data)
        """
        subject = subject.lower()
        
        if subject == "math":
            is_valid, error = self.math_validator.validate(question, answer)
            return is_valid, {"error_message": error, "subject": subject}
        
        elif subject in ["science", "history", "arts", "geography", "literature"]:
            return self.fact_validator.validate(question, answer, sources)
        
        else:
            return False, {"error_message": f"Unknown subject: {subject}", "subject": subject}