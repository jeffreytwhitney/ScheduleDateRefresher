import os
from datetime import datetime

import DB
import INIConfig


class LogWriter:
    def __init__(self, log_file_name, log_file_max_line_count):
        self._log_file_name: str = log_file_name
        self._log_file_max_line_count: int = log_file_max_line_count
        self._log_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), log_file_name)

    def write_log_to_file(self, log_message: str):
        with open(self._log_file_path, "a") as log_file:
            log_file.write(log_message + "\n")
        self._trim_log_file(self._log_file_path, self._log_file_max_line_count)

    def _trim_log_file(self, file_path, max_lines):
        with open(file_path, "r") as file:
            lines = file.readlines()

        if len(lines) > max_lines:
            with open(file_path, "w") as file:
                file.writelines(lines[-max_lines:])


class Logger:
    _log_to_screen: bool
    _log_to_file: bool
    _log_file_name: str
    _log_file_max_line_count: int
    _log_writer: LogWriter

    def __init__(self):
        self._log_to_screen = bool(INIConfig.GetStoredIniValue("Logging", "log_to_screen", "ScheduleImporter"))
        self._log_to_file = bool(INIConfig.GetStoredIniValue("Logging", "log_to_file", "ScheduleImporter"))
        self._log_file_name = INIConfig.GetStoredIniValue("Logging", "log_file_name", "ScheduleImporter")
        self._log_file_max_line_count = int(INIConfig.GetStoredIniValue("Logging", "log_file_max_line_count", "ScheduleImporter"))
        self._log_writer = LogWriter(self._log_file_name, self._log_file_max_line_count)

    def log_error(self, error_message: str):
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"DATE/TIME: {current_datetime}.     ERROR: {error_message}"
        if self._log_to_screen:
            print(full_message)
        if self._log_to_file:
            self._log_writer.write_log_to_file(full_message)

    def log_message(self, info_message: str):
        current_datetime = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        full_message = f"DATE/TIME: {current_datetime}.     MESSAGE: {info_message}"
        if self._log_to_screen:
            print(full_message)
        if self._log_to_file:
            self._log_writer.write_log_to_file(full_message)

    def log_schedule_run_error(self, runid, schedule_id, error_message: str):
        self.log_error(error_message)
        self._write_error_to_db(runid, schedule_id, error_message)

    def log_schedule_run_message(self, runid, schedule_id, log_message: str):
        self.log_message(log_message)
        self._write_log_to_db(runid, schedule_id, log_message)

    def _write_error_to_db(self, runid, schedule_id, error_message: str):
        sql: str = f"Insert into tblScheduleRunLog (ScheduleRunEntryID, ScheduleID, LogMessage, IsError) values ({runid}, {schedule_id}, '{error_message}', 1)"
        DB.execute_sql_statement(sql)

    def _write_log_to_db(self, runid, schedule_id, log_message: str):
        sql: str = f"Insert into tblScheduleRunLog (ScheduleRunEntryID, ScheduleID, LogMessage, IsError) values ({runid}, {schedule_id}, '{log_message}', 0)"
        DB.execute_sql_statement(sql)
