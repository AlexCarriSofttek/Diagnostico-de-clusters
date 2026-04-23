import logging
from datetime import date

def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        filename=f"diagnostico_{date.today()}.log",
        filemode="a",
    )
