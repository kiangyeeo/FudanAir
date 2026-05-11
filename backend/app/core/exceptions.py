from __future__ import annotations


class AppException(Exception):
    code: str = "INTERNAL_ERROR"
    message: str = "系统繁忙,请稍后重试"
    http_status: int = 500

    def __init__(self, message: str = "") -> None:
        self.message = message or self.message
        super().__init__(self.message)

    def to_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": self.message}


class AuthenticationError(AppException):
    code = "AUTHENTICATION_FAILED"
    message = "认证失败"
    http_status = 401


class UnauthorizedError(AppException):
    code = "UNAUTHORIZED"
    message = "未登录或登录已失效"
    http_status = 401


class PermissionDeniedError(AppException):
    code = "PERMISSION_DENIED"
    message = "无权限"
    http_status = 403


class ResourceNotFoundError(AppException):
    code = "RESOURCE_NOT_FOUND"
    message = "资源不存在"
    http_status = 404


class ResourceInUseError(AppException):
    code = "RESOURCE_IN_USE"
    message = "资源被引用,无法删除"
    http_status = 409


class PhoneAlreadyExistsError(AppException):
    code = "PHONE_ALREADY_EXISTS"
    message = "手机号已注册"
    http_status = 409


class InsufficientStockError(AppException):
    code = "INSUFFICIENT_STOCK"
    message = "库存不足"
    http_status = 409


class PassengerDuplicateError(AppException):
    code = "PASSENGER_DUPLICATE"
    message = "同一乘机人在该航班实例已有有效票"
    http_status = 409


class InstanceNotBookableError(AppException):
    code = "INSTANCE_NOT_BOOKABLE"
    message = "航班实例不可订"
    http_status = 409


class OrderNotPayableError(AppException):
    code = "ORDER_NOT_PAYABLE"
    message = "订单不可支付"
    http_status = 409


class OrderNotCancelableError(AppException):
    code = "ORDER_NOT_CANCELABLE"
    message = "订单不可取消"
    http_status = 409


class TicketNotRefundableError(AppException):
    code = "TICKET_NOT_REFUNDABLE"
    message = "客票不可退"
    http_status = 409


class TicketNotChangeableError(AppException):
    code = "TICKET_NOT_CHANGEABLE"
    message = "客票不可改"
    http_status = 409


class InvalidPhoneFormatError(AppException):
    code = "INVALID_PHONE_FORMAT"
    message = "手机号格式错误"
    http_status = 400


class OldPasswordMismatchError(AppException):
    code = "OLD_PASSWORD_MISMATCH"
    message = "原密码错误"
    http_status = 400


class InconsistentAirportCityError(AppException):
    code = "INCONSISTENT_AIRPORT_CITY"
    message = "机场所属城市与临近机场关系不一致"
    http_status = 400


class SameTicketNotAllowedError(AppException):
    code = "SAME_TICKET_NOT_ALLOWED"
    message = "改签目标不能与原票相同"
    http_status = 400
