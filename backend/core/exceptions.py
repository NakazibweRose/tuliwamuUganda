"""Consistent error envelope: {"error": {"code", "message", "details"}}."""
from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    code = getattr(exc, "default_code", "error")
    if isinstance(data, dict) and "detail" in data and len(data) == 1:
        message, details = str(data["detail"]), None
        code = getattr(data["detail"], "code", code)
    else:
        message, details = "Please check the highlighted fields.", data
        code = "validation_error" if response.status_code == 400 else code
    response.data = {"error": {"code": str(code), "message": message, "details": details}}
    return response
