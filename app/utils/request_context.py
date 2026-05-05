import contextvars
from dataclasses import dataclass


request_id_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_id", default=None)
request_method_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_method", default=None)
request_path_template_var: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "request_path_template", default=None
)
request_handler_var: contextvars.ContextVar[str | None] = contextvars.ContextVar("request_handler", default=None)


@dataclass(frozen=True)
class RequestContextSnapshot:
    request_id: str | None
    method: str | None
    path_template: str | None
    handler: str | None


def snapshot() -> RequestContextSnapshot:
    return RequestContextSnapshot(
        request_id=request_id_var.get(),
        method=request_method_var.get(),
        path_template=request_path_template_var.get(),
        handler=request_handler_var.get(),
    )

