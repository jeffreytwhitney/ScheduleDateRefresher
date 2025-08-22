import logging
import DB


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

