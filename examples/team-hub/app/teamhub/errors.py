"""One error type per HTTP status; the API turns them into {"error": {"code", "message"}}."""


class AppError(Exception):
    status = 400
    code = "invalid"

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class Invalid(AppError):
    status, code = 400, "invalid"


class Unauthorized(AppError):
    status, code = 401, "unauthorized"


class Forbidden(AppError):
    status, code = 403, "forbidden"


class NotFound(AppError):
    status, code = 404, "not_found"


class Conflict(AppError):
    status, code = 409, "conflict"


class MethodNotAllowed(AppError):
    status, code = 405, "method_not_allowed"
