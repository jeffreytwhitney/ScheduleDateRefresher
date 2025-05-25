from dataclasses import dataclass
from datetime import datetime

import DB


@dataclass
class ScheduleRunConfig:
    schedule_run_id: int
    run_datetime: datetime
    start_date: datetime
    end_date: datetime
    request_user_employee_number: str
    request_user_name: str
    is_automated: bool
    is_complete: str


class ScheduleRun:
    def __init__(self, site_id: int):
        self._site_id = site_id
        sql: str = f"Select Count(*) from dbo.tblScheduleRunEntry where SiteID = {self._site_id} AND IsComplete = 0"
        count = DB.get_sql_scalar(sql)
        self._is_runnable = count > 0

        if self._is_runnable:
            self._schedule_run_config = self._get_schedule_run_config()

    @property
    def is_runnable(self) -> bool:
        return self._is_runnable

    @property
    def is_complete(self) -> bool:
        return self._schedule_run_config.is_complete == 1

    @property
    def schedule_run_id(self) -> int:
        return self._schedule_run_config.schedule_run_id

    @property
    def run_datetime(self) -> datetime:
        return self._schedule_run_config.run_datetime

    @property
    def start_date(self) -> datetime:
        return self._schedule_run_config.start_date

    @property
    def end_date(self) -> datetime:
        return self._schedule_run_config.end_date

    @property
    def request_user_employee_number(self) -> str:
        return self._schedule_run_config.request_user_employee_number

    @property
    def request_user_name(self) -> str:
        return self._schedule_run_config.request_user_name

    @property
    def is_automated(self) -> bool:
        return self._schedule_run_config.is_automated

    def start_run(self) -> None:
        sql: str = f"Update dbo.tblScheduleRunEntry set StartTimestamp = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' where ID = {self._schedule_run_config.schedule_run_id}"
        DB.execute_sql_statement(sql)

    def complete_run(self) -> None:
        sql: str = f"Update dbo.tblScheduleRunEntry set CompletionTimestamp = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}', IsComplete = 1 where ID = {self._schedule_run_config.schedule_run_id}"

    def _get_schedule_run_config(self):
        sql: str = f"Select * from dbo.qryUncompletedScheduleRunTimes where SiteID = {self._site_id} AND IsComplete = 0 order by ID"
        record = DB.get_sql_recordset(sql)[0]
        return ScheduleRunConfig(
            record['ID'],
            record['RunDateTime'],
            record['StartTimestamp'],
            record['CompletionTimestamp'],
            record['RequestUserEmployeeNumber'],
            record['RequesterName'],
            record['IsAutomated'],
            record['IsComplete'])
