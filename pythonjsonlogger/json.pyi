import logging


class JsonFormatter(logging.Formatter):
    def __init__(self, *args: object, **kwargs: object) -> None: ...
    def add_fields(
        self,
        log_record: dict[str, object],
        record: logging.LogRecord,
        message_dict: dict[str, object],
    ) -> None: ...
