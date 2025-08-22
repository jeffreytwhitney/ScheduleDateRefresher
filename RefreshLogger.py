import logging
import os
import sys

import DB
import INIConfig


class SQLServerHandler(logging.Handler):
    def __init__(self):
        super().__init__()

    def emit(self, record):
        if record.levelname == "ERROR":
            is_error = 1
        else:
            is_error = 0

        run_id = list(getattr(record, 'runid', None))[0]
        schedule_id = list(getattr(record, 'scheduleid', None))[0]
        if not run_id or not schedule_id:
            return

        sql: str = f"Insert into tblScheduleRunLog (ScheduleRunEntryID, ScheduleID, LogMessage, IsError) values ({run_id}, {schedule_id}, '{record.getMessage()}', {is_error})"
        DB.execute_sql_statement(sql)

    def close(self):
        super().close()


def get_current_directory():
    if getattr(sys, 'frozen', False):  # Check if running as an executable
        return os.path.dirname(sys.executable)
    else:  # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def get_logger(logger_name) -> logging.Logger:
    logger = logging.getLogger(logger_name)
    logger_level = INIConfig.GetStoredIniValue("Loggers", logger_name, "ScheduleImporter")
    if logger_level == "DEBUG":
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    file_handler = logging.FileHandler(get_current_directory() + "\\ScheduleRefreshLog.txt")
    if logger_level == "DEBUG":
        file_handler.setLevel(logging.DEBUG)
    else:
        file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    return logger


def get_db_logger() -> logging.Logger:
    db_logger = logging.getLogger("db_logger")
    db_logger.setLevel(logging.INFO)
    formatter = logging.Formatter('%(name)s - %(levelname)s - %(message)s')
    sql_handler = SQLServerHandler()
    sql_handler.setLevel(logging.DEBUG)
    sql_handler.setFormatter(formatter)
    db_logger.addHandler(sql_handler)

    return db_logger


