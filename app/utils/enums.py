from enum import Enum


class ExtendedEnum(Enum):

    @classmethod
    def get_list(cls):
        return [c.value for c in cls]


class EmailVerificationStatus(ExtendedEnum):
    VERIFIED = 1
    INVALID_TOKEN = 0
    ALREADY_VERIFIED = -1


class FeedbackType(ExtendedEnum):
    ERROR = "error"
    SUCCESS = "success"
    INFO = "info"
    WARNING = "warning"


class RequestMethod(ExtendedEnum):
    GET = "get"
    POST = "post"
    PATCH = "patch"
    DELETE = "delete"


class DatabaseFilterOperator(ExtendedEnum):
    EQUAL = "="
    NOT_EQUAL = "<>"
    LESS_THAN = "<"
    LESS_THAN_OR_EQUAL = "<="
    GREATER_THAN = ">"
    GREATER_THAN_OR_EQUAL = ">="
    LIKE = "LIKE"
    IS_NOT = "!="


class Frequency(ExtendedEnum):
    ONCE = 1
    DAILY = 2
    WEEKLY = 3
    MONTHLY = 4
    YEARLY = 5
