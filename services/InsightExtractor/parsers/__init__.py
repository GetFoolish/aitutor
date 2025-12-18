"""Email parsers for extracting learning insights"""
from .course_parser import CourseParser
from .newsletter_parser import NewsletterParser
from .certificate_parser import CertificateParser

__all__ = ['CourseParser', 'NewsletterParser', 'CertificateParser']
