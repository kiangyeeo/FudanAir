from __future__ import annotations


class AppException(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = "The system is busy. Please try again later."
    http_status: int = 500

    def __init__(self, message: str = "") -> None:
        self.message = message or self.message
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class AuthenticationError(AppException):
    code = "AUTHENTICATION_FAILED"
    message = "Authentication failed."
    http_status = 401


class UnauthorizedError(AppException):
    code = "UNAUTHORIZED"
    message = "You are not signed in or your session has expired."
    http_status = 401


class PermissionDeniedError(AppException):
    code = "PERMISSION_DENIED"
    message = "Permission denied."
    http_status = 403


class ResourceNotFoundError(AppException):
    code = "RESOURCE_NOT_FOUND"
    message = "Resource not found."
    http_status = 404


class ResourceInUseError(AppException):
    code = "RESOURCE_IN_USE"
    message = "This resource is in use and cannot be deleted."
    http_status = 409


class PhoneAlreadyExistsError(AppException):
    code = "PHONE_ALREADY_EXISTS"
    message = "This phone number is already registered."
    http_status = 409


class InsufficientStockError(AppException):
    code = "INSUFFICIENT_STOCK"
    message = "Insufficient inventory."
    http_status = 409


class PassengerDuplicateError(AppException):
    code = "PASSENGER_DUPLICATE"
    message = "This passenger already has an active ticket for this flight instance."
    http_status = 409


class InstanceNotBookableError(AppException):
    code = "INSTANCE_NOT_BOOKABLE"
    message = "This flight instance is not bookable."
    http_status = 409


class OrderNotPayableError(AppException):
    code = "ORDER_NOT_PAYABLE"
    message = "This order cannot be paid."
    http_status = 409


class OrderNotCancelableError(AppException):
    code = "ORDER_NOT_CANCELABLE"
    message = "This order cannot be canceled."
    http_status = 409


class TicketNotRefundableError(AppException):
    code = "TICKET_NOT_REFUNDABLE"
    message = "This ticket cannot be refunded."
    http_status = 409


class TicketNotChangeableError(AppException):
    code = "TICKET_NOT_CHANGEABLE"
    message = "This ticket cannot be changed."
    http_status = 409


class InvalidPhoneFormatError(AppException):
    code = "INVALID_PHONE_FORMAT"
    message = "Invalid phone number format."
    http_status = 400


class OldPasswordMismatchError(AppException):
    code = "OLD_PASSWORD_MISMATCH"
    message = "The current password is incorrect."
    http_status = 400


class InconsistentAirportCityError(AppException):
    code = "INCONSISTENT_AIRPORT_CITY"
    message = "The airport city is inconsistent with the nearby-airport relation."
    http_status = 400


class SameTicketNotAllowedError(AppException):
    code = "SAME_TICKET_NOT_ALLOWED"
    message = "The change target cannot be the same as the original ticket."
    http_status = 400
