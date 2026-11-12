"""Errors the services raise. The HTTP layer turns each into a status code and a message."""


class ServiceError(Exception):
    status_code = 400
    code = "bad_request"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidDestination(ServiceError):
    code = "invalid_url"


class InvalidCode(ServiceError):
    code = "invalid_code"


class CodeTaken(ServiceError):
    status_code = 409
    code = "code_taken"


class LinkNotFound(ServiceError):
    status_code = 404
    code = "not_found"


class EditKeyRequired(ServiceError):
    status_code = 401
    code = "edit_key_required"


class EditKeyInvalid(ServiceError):
    status_code = 403
    code = "edit_key_invalid"


class NoFreeCode(ServiceError):
    status_code = 503
    code = "no_free_code"
