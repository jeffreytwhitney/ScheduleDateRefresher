import os
from dataclasses import dataclass
from datetime import datetime, timedelta, time
import logging
import DB
import INIConfig
import RefreshLogger


def get_local_user_id() -> str:
    username = os.getlogin().upper()
    sql = f"Select EmployeeNumber from tblUser where IsActive = 1 and NetworkUserName = '{username}'"
    user_id = str(DB.get_sql_scalar(sql))
    return user_id


@dataclass
class ScheduleRunConfig:
    schedule_run_id: int
    request_user_employee_number: str
    is_automated: bool


class ScheduleRun:
    _is_runnable: bool = False
    _run_local: bool = False
    _run_local_employee_number: str = ""
    _site_id: int = 0
    _schedule_run_config: ScheduleRunConfig = None
    _logger: logging.Logger

    def __init__(self, site_id: int):

        self._logger = RefreshLogger.get_logger('scheduleRunLogger')

        self._site_id = site_id
        run_local_integer = int(INIConfig.GetStoredIniValue("Switches", "run_local", "ScheduleImporter"))
        self._logger.debug(f"Run Local: {run_local_integer}")

        self._run_local = run_local_integer > 0

        if self._run_local:
            self._run_local_employee_number = get_local_user_id()
            self._logger.debug(f"Run Local Employee Number: {self._run_local_employee_number}")

            self._create_local_run_entry()

        sql: str = f"Select Count(*) from dbo.tblScheduleRunEntry where SiteID = {self._site_id} AND IsComplete = 0 AND StartTimestamp IS NULL AND RunDateTime < GetDate()"
        count = DB.get_sql_scalar(sql)
        self._logger.debug(f"Runnable Count: {count}")
        self._is_runnable = count > 0

        if self._is_runnable:
            self._logger.debug("Schedule Run is runnable.")
            self._schedule_run_config = self._get_schedule_run_config()

    @property
    def is_runnable(self) -> bool:
        return self._is_runnable

    @property
    def schedule_run_id(self) -> int:
        return self._schedule_run_config.schedule_run_id

    def start_run(self) -> None:
        self._logger.debug("Starting schedule run.")
        sql: str = f"Update dbo.tblScheduleRunEntry set StartTimestamp = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}' where ID = {self._schedule_run_config.schedule_run_id}"
        DB.execute_sql_statement(sql)

    def complete_run(self, error_count: int = 0, updated_task_count: int = 0) -> None:
        self._logger.debug("Completing schedule run.")
        sql: str = f"Update dbo.tblScheduleRunEntry set CompletionTimestamp = '{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}', IsComplete = 1, HasErrors = {error_count}, TasksUpdated = {updated_task_count} where ID = {self._schedule_run_config.schedule_run_id}"
        DB.execute_sql_statement(sql)
        if not self._run_local:
            self._create_automated_run_entry()

    def _get_schedule_run_config(self):
        self._logger.debug("Getting schedule run configuration.")
        sql: str = f"Select * from dbo.qryUncompletedScheduleRunTimes where SiteID = {self._site_id} AND IsComplete = 0 order by ID"
        record = DB.get_sql_recordset(sql)[0]
        return ScheduleRunConfig(
            record['ID'],
            record['RequestUserEmployeeNumber'],
            record['IsAutomated'])

    def _create_local_run_entry(self):
        self._logger.debug("Creating local run entry.")
        create_datetime = datetime.now() - timedelta(minutes=1)
        sql: str = f"Update dbo.tblScheduleRunEntry Set IsComplete = 1 WHERE SiteID = {self._site_id} AND IsComplete = 0 And IsAutomated = 0"
        DB.execute_sql_statement(sql)
        sql: str = (f"Insert into dbo.tblScheduleRunEntry (SiteID, RunDateTime, RequestUserEmployeeNumber, IsAutomated) values ({self._site_id}, "
                    f"'{create_datetime.strftime('%Y-%m-%d %H:%M:%S')}', '{self._run_local_employee_number}', 0)")
        DB.execute_sql_statement(sql)

    def _create_automated_run_entry(self):
        self._logger.debug("Creating automated run entry.")
        create_datetime = self._generate_new_run_datetime()
        sql: str = ""
        sql = f"Select Count(*) from dbo.tblScheduleRunEntry where SiteID = {self._site_id} and IsAutomated = 1 and IsComplete = 0 and StartTimestamp Is Null and RunDateTime = '{create_datetime}'"
        count_of_runs = int(DB.get_sql_scalar(sql))

        if count_of_runs == 0:
            sql = f"Insert into dbo.tblScheduleRunEntry (SiteID, RunDateTime, IsAutomated) values ({self._site_id}, '{create_datetime}', 1)"
            DB.execute_sql_statement(sql)

    def _generate_new_run_datetime(self):
        self._logger.debug("Generating new run datetime.")
        current_time = datetime.now().time()
        current_date = datetime.now().date()
        next_run_time: time = current_time
        sql: str = "Select RunTime from tblScheduleRunTimes where SiteID = {site_id} order by RunTime".format(site_id=self._site_id)
        runtimes = DB.get_sql_recordset(sql)
        for r in runtimes:
            run_time = r["RunTime"]
            if run_time > current_time:
                next_run_time = run_time
                break

        if next_run_time > current_time:
            return datetime.combine(current_date, next_run_time).strftime("%Y-%m-%d %H:%M:%S")
        else:
            run_time = runtimes[0]["RunTime"]
            current_date += timedelta(days=1)
            return datetime.combine(current_date, run_time).strftime("%Y-%m-%d %H:%M:%S")
