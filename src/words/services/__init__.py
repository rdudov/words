"""
Business logic services for the Words application.

This package provides service layer classes that orchestrate business logic
between repositories and application handlers. Services handle complex
operations, validation, and coordination of multiple repository calls.

Available Services:
- UserService: User management and language profile operations
"""

from .user import UserService

__all__ = ["UserService"]
