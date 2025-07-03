from datetime import datetime, timedelta
from typing import List

import DB
from Logger import Logger


def prev_weekday(adate):
    adate -= timedelta(days=1)
    while adate.weekday() > 4:
        adate -= timedelta(days=1)
    return adate


class Task:
    _updated: bool = False
    _id: int
    _projectid: int
    _statusid: int
    _taskname: str
    _duedate: datetime
    _scheduledduedate: datetime
    _datestarted: datetime
    _updatedtimestamp: datetime
    _updateuserid: str
    _currently_running: bool = False

    def __init__(self, iid: int, projectid: int, statusid: int, taskname: str, duedate: datetime,
                 scheduledduedate: datetime):
        self._id = iid
        self._projectid = projectid
        self._statusid = statusid
        self._taskname = taskname
        self._duedate = duedate
        self._scheduledduedate = scheduledduedate

    @property
    def task_id(self) -> int:
        return self._id

    @property
    def is_currently_running(self) -> bool:
        return self._currently_running

    @is_currently_running.setter
    def is_currently_running(self, value: bool) -> None:
        self._currently_running = value

    @property
    def is_updated(self) -> bool:
        return self._updated

    @property
    def projectid(self) -> int:
        return self._projectid

    @property
    def statusid(self) -> int:
        return self._statusid

    @property
    def taskname(self) -> str:
        return self._taskname

    @property
    def duedate(self) -> datetime:
        return self._duedate

    @property
    def scheduledduedate(self) -> datetime:
        return self._scheduledduedate


class TaskWriter:

    def __init__(self, site_id: int):
        self._updated = None
        self._site_id = site_id
        self._tasks = self._get_tasks()
        self._logger = Logger()

    def _get_tasks(self) -> List[Task]:
        ACTIVE_TASKS_QUERY = "SELECT * FROM qryTaskList WHERE ManualDueDate = 0 AND StatusID Not In (4,5) AND SiteID = {site_id}"
        records = DB.get_sql_recordset(ACTIVE_TASKS_QUERY.format(site_id=self._site_id))
        return [self._create_task_from_record(record) for record in records]

    def _create_task_from_record(self, record: dict) -> Task:
        config = Task(
            iid=record['ID'],
            projectid=record['ProjectID'],
            statusid=record['StatusID'],
            taskname=record['TaskName'],
            duedate=datetime.strptime(record['DueDate'], "%m/%d/%y"),
            scheduledduedate=datetime.strptime(record['ScheduledDueDate'], "%m/%d/%y")
        )

        return Task(
            config.task_id,
            config.projectid,
            config.statusid,
            config.taskname,
            config.duedate,
            config.scheduledduedate
        )

    @property
    def updated_tasks(self) -> List[Task]:
        return [task for task in self._tasks if task.is_updated]

    @property
    def currently_running_tasks(self) -> List[Task]:
        return [task for task in self._tasks if task.is_currently_running]

    def get_tasks_by_name(self, task_name: str) -> List[Task]:
        return [task for task in self._tasks if task.taskname == task_name]

    def get_currently_running_tasks(self) -> List[Task]:
        return [task for task in self._tasks if task.is_currently_running]

    def get_updated_tasks(self) -> List[Task]:
        return [task for task in self._tasks if task.is_updated]

    def update_dates_by_taskname(self, task_name: str, xl_due_date: datetime) -> None:

        tasks = self.get_tasks_by_name(task_name)
        for task in tasks:
            if task.scheduledduedate == xl_due_date:
                # task already has the same date, no need to update it
                continue

            task._scheduledduedate = xl_due_date
            task._duedate = prev_weekday(xl_due_date)
            task._updated = True
            if task.statusid == 7:
                task._statusid = 1

    def write_currently_running_tasks_to_database(self) -> None:
        with DB.DatabaseConnection(False) as db:
            sql_statement = f"UPDATE tblTask SET CurrentlyRunning = 0"
            db.execute_statement(sql_statement)
            for task in self.get_currently_running_tasks():
                sql_statement = f"UPDATE tblTask SET CurrentlyRunning = 1 WHERE ID = {task.task_id}"
                try:
                    db.execute_statement(sql_statement)
                except Exception as e:
                    self._logger.log_error(f"Database error while updating Task Record. SQL statement: {sql_statement}")

    def write_updated_tasks_to_database(self) -> None:

        with DB.DatabaseConnection(False) as db:
            for task in self.get_updated_tasks():
                if task.statusid == 7:
                    sql_statement = f"UPDATE tblTask SET StatusID = 1, DueDate = '{task.duedate}', ScheduledDueDate = '{task.scheduledduedate}' WHERE ID = {task.task_id}"
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.log_error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
                else:
                    sql_statement = f"UPDATE tblTask SET DueDate = '{task.duedate}', ScheduledDueDate = '{task.scheduledduedate}' WHERE ID = {task.task_id}"
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.log_error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
