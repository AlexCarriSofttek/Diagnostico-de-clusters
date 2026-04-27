import logging
from datetime import datetime, date
from zoneinfo import ZoneInfo

class LocalTZFormatter(logging.Formatter):
    def formatTime(self, record, datefmt=None):
        dt = datetime.fromtimestamp(
            record.created,
            tz=ZoneInfo("America/Mexico_City")
        )
        return dt.strftime(datefmt or "%Y-%m-%d %H:%M:%S")

def setup_logging():
    log_file = f"diagnostico_{date.today()}.log"

    handler = logging.FileHandler(
        log_file,
        mode="a",
        encoding="utf-8"
    )

    formatter = LocalTZFormatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    # Evita logs duplicados si setup_logging se llama más de una vez
    root_logger.handlers.clear()
    root_logger.addHandler(handler)
