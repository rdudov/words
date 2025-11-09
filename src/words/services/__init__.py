"""
Business logic services for the Words application.

This package provides service layer classes that orchestrate business logic
between repositories and application handlers. Services handle complex
operations, validation, and coordination of multiple repository calls.

Available Services:
- UserService: User management and language profile operations
- TranslationService: LLM-based word translation and answer validation with caching
"""

from .user import UserService
from .translation import TranslationService

__all__ = ["UserService", "TranslationService"]
