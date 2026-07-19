"""
app/core/exceptions.py

Custom exceptions for Medical AI Analyzer.
"""


class MedicalAnalyzerException(Exception):
    """
    Base exception for application.
    """

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class AIServiceError(MedicalAnalyzerException):
    """
    Error related to AI communication.
    """
    pass


class OCRException(MedicalAnalyzerException):
    """
    Error during OCR processing.
    """
    pass


class DocumentProcessingError(MedicalAnalyzerException):
    """
    Error during document processing.
    """
    pass


class UnsupportedDocumentError(MedicalAnalyzerException):
    """
    Unsupported medical document type.
    """
    pass


class FileValidationError(MedicalAnalyzerException):
    """
    Invalid uploaded file.
    """
    pass