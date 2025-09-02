from datetime import datetime, timedelta
from typing import List
import DB
import INIConfig
import RefreshLogger
import logging


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


def _create_task_from_record(record: dict) -> Task:
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


class TaskWriter:
    _automated_user_id: str
    _logger: logging.Logger

    def __init__(self, site_id: int):
        self._updated = None
        self._site_id = site_id
        self._tasks = self._get_tasks()
        self._automated_user_id = str(INIConfig.GetStoredIniValue("Site", "automated_user_id", "ScheduleImporter"))
        self._logger = RefreshLogger.get_logger('taskLogger')

    def _get_tasks(self) -> List[Task]:
        active_tasks_query = "SELECT * FROM qryTaskList WHERE ManualDueDate = 0 AND StatusID Not In (4,5) AND SiteID = {site_id}"
        records = DB.get_sql_recordset(active_tasks_query.format(site_id=self._site_id))
        return [_create_task_from_record(record) for record in records]

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
            if task.scheduledduedate == xl_due_date and task.statusid != 7:
                # task already has the same date, no need to update it
                continue
            self._logger.debug(f"Updating due date for task '{task_name}' to '{xl_due_date}'")
            task._scheduledduedate = xl_due_date
            task._duedate = prev_weekday(xl_due_date)
            task._updated = True

    def update_db_auto_not_scheduled(self):
        self._logger.debug("Updating database with auto not scheduled tasks.")
        with DB.DatabaseConnection(False) as db:
            sql_statement = (f"UPDATE dbo.tblTask SET tblTask.StatusID = 7 FROM tblProject RIGHT OUTER JOIN tblTask ON "
                             f"tblProject.ID = dbo.tblTask.ProjectID WHERE tblTask.StatusID = 1 AND "
                             f"dbo.tblProject.SiteID = {self._site_id} AND dbo.tblTask.ManualDueDate = 0 AND "
                             f"dbo.tblTask.AssignedToID IS NOT NULL AND NOT dbo.tblTask.TaskName IN "
                             f"(SELECT TaskName FROM dbo.tblImportMachineName WHERE SiteID = {self._site_id})")
            db.execute_statement(sql_statement)

    def write_active_task_counts_to_database(self) -> None:
        self._logger.debug("Writing active task counts to database.")
        with DB.DatabaseConnection(False) as db:
            sql_statement = f"update tblProject set CountOfActiveTasks = 0 where SiteID = {self._site_id}"
            db.execute_statement(sql_statement)
            sql_statement = (f"Update tblProject SET tblProject.CountOfActiveTasks = qryCountOfActiveTasks.CountOfID FROM "
                             f"dbo.tblProject INNER JOIN dbo.qryCountOfActiveTasks ON dbo.tblProject.ID = "
                             f"dbo.qryCountOfActiveTasks.ProjectID WHERE tblProject.SiteID = {self._site_id}")
            db.execute_statement(sql_statement)

    def write_currently_running_tasks_to_database(self) -> None:
        self._logger.debug("Writing currently running tasks to database.")
        with DB.DatabaseConnection(False) as db:
            self._logger.debug("Reset all currently running tasks.")
            sql_statement = (f"UPDATE tblTask SET CurrentlyRunning = 0 FROM tblProject RIGHT OUTER JOIN tblTask ON "
                             f"tblProject.ID = tblTask.ProjectID WHERE tblProject.SiteID = {self._site_id}")
            db.execute_statement(sql_statement)
            for task in self.get_currently_running_tasks():
                if task.statusid == 7:
                    self._logger.debug(
                        f"Setting 'Not Schedled' task '{task.taskname}' to currently running and setting status to 'Not Started'.")
                    sql_statement = f"UPDATE tblTask SET StatusID = 1, CurrentlyRunning = 1 WHERE ID = {task.task_id}"
                else:
                    self._logger.debug(f"Setting task '{task.taskname}' to currently running.")
                    sql_statement = f"UPDATE tblTask SET CurrentlyRunning = 1 WHERE ID = {task.task_id}"
                try:
                    db.execute_statement(sql_statement)
                except Exception as e:
                    self._logger.error(f"Database error while updating Task Record. SQL statement: {sql_statement}")

    def write_updated_tasks_to_database(self) -> None:

        with DB.DatabaseConnection(False) as db:
            for task in self.get_updated_tasks():
                if task.statusid == 7:
                    self._logger.debug(f"Updating 'Not Schedled' task '{task.taskname}' to due "
                                       f"date {task.duedate} and setting status to 'Not Started'.")
                    sql_statement = (f"UPDATE tblTask SET StatusID = 1, DueDate = '{task.duedate}', "
                                     f"ScheduledDueDate = '{task.scheduledduedate}', "
                                     f"UpdateUserID = '{self._automated_user_id}', "
                                     f"UpdatedTimestamp = CURRENT_TIMESTAMP WHERE ID = {task.task_id}")
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
                else:
                    self._logger.debug(f"Updating task '{task.taskname}' to due date {task.duedate}.")
                    sql_statement = (f"UPDATE tblTask SET DueDate = '{task.duedate}', ScheduledDueDate = '{task.scheduledduedate}', "
                                     f"UpdateUserID = '{self._automated_user_id}', "
                                     f"UpdatedTimestamp = CURRENT_TIMESTAMP WHERE ID = {task.task_id}")
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
