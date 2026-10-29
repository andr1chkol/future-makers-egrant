class DomainError(Exception):
    def __init__(self, code: str, status: int, message: str, details: dict | None = None):
        self.code = code
        self.status = status
        self.message = message
        self.details = details
        super().__init__(code)


class UnavailableError(DomainError):
    def __init__(self):
        super().__init__("FEATURE_UNAVAILABLE", 503, "This feature is not implemented yet")


class NotFoundError(DomainError):
    def __init__(self):
        super().__init__("NOT_FOUND", 404, "Resource not found")


class ConflictError(DomainError):
    def __init__(self):
        super().__init__("CONFLICT", 409, "Resource state conflicts with this operation")


class ValidationError(DomainError):
    def __init__(self):
        super().__init__("VALIDATION_ERROR", 422, "Invalid input")
