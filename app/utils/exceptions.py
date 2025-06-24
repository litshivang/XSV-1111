class AppError(Exception):
    """Base exception for the travel AI agent app."""
    pass

class EmailServiceError(AppError):
    """Raised when there is an error in the email service."""
    pass

class AIServiceError(AppError):
    """Raised when there is an error in the AI extraction service."""
    pass

class ExcelServiceError(AppError):
    """Raised when there is an error in the Excel generation service."""
    pass

class ValidationError(AppError):
    """Raised when data validation fails."""
    pass
