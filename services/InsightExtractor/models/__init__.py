"""Data models for InsightExtractor"""
from .schemas import (
    EmailSignal,
    ExtractedCourse,
    ExtractedNewsletter,
    ExtractedCertificate,
    LearningInsight,
    ColdStartProfile,
    InsightExtractionRequest,
    InsightExtractionResponse
)

__all__ = [
    'EmailSignal',
    'ExtractedCourse',
    'ExtractedNewsletter',
    'ExtractedCertificate',
    'LearningInsight',
    'ColdStartProfile',
    'InsightExtractionRequest',
    'InsightExtractionResponse'
]
