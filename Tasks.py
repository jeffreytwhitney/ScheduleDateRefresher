from datetime import datetime, timedelta
from typing import List

import DB
import INIConfig
import logging.config


def prev_weekday(adate):
    adate -= timedelta(days=1)
    while adate.weekday() > 4:
        adate -= timedelta(days=1)
    return adate


class Task:
    """
    Represents a task within a project management system.

    This class is used to define the properties and status of a task. It includes
    information such as the task's ID, associated project ID, status ID, task name,
    due date, and whether the task is currently running or updated. It provides
    properties to safely access these attributes.

    :ivar task_id: Unique identifier for the task.
    :type task_id: int
    :ivar is_currently_running: Indicates if the task is currently running.
    :type is_currently_running: bool
    :ivar is_updated: Indicates whether the task's information has been updated.
    :type is_updated: bool
    :ivar projectid: Identifier of the project to which the task belongs.
    :type projectid: int
    :ivar statusid: Status ID representing the current status of the task.
    :type statusid: int
    :ivar taskname: Name of the task.
    :type taskname: str
    :ivar duedate: Due date of the task.
    :type duedate: datetime
    :ivar scheduledduedate: Scheduled due date of the task.
    :type scheduledduedate: datetime
    """
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
    """
    Handles the management, manipulation, and updating of task objects for a specific site.

    Provides functionality to interact with a set of tasks, which includes filtering,
    retrieving, and updating tasks based on specific criteria. The class also handles
    the synchronization of task data with the database, ensuring that any changes
    ```arepython reflected
     persist"""
    _automated_user_id: str
    _logger: logging.Logger

    def __init__(self, site_id: int):
        self._updated = None
        self._site_id = site_id
        self._tasks = self._get_tasks()
        self._automated_user_id = str(INIConfig.GetStoredIniValue("Site", "automated_user_id", "ScheduleImporter"))
        logging.config.fileConfig('logging.conf')
        self._logger = logging.getLogger('taskLogger')

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
            sql_statement = f"UPDATE dbo.tblTask SET tblTask.StatusID = 7 FROM tblProject RIGHT OUTER JOIN tblTask ON tblProject.ID = dbo.tblTask.ProjectID WHERE tblTask.StatusID = 1 AND dbo.tblProject.SiteID = {self._site_id} AND dbo.tblTask.ManualDueDate = 0 AND dbo.tblTask.AssignedToID IS NOT NULL AND NOT dbo.tblTask.TaskName IN (SELECT TaskName FROM dbo.tblImportMachineName WHERE SiteID = {self._site_id})"
            db.execute_statement(sql_statement)

    def write_currently_running_tasks_to_database(self) -> None:
        self._logger.debug("Writing currently running tasks to database.")
        with DB.DatabaseConnection(False) as db:
            self._logger.debug("Reset all currently running tasks.")
            sql_statement = f"UPDATE tblTask SET CurrentlyRunning = 0 FROM tblProject RIGHT OUTER JOIN tblTask ON tblProject.ID = tblTask.ProjectID WHERE tblProject.SiteID = {self._site_id}"
            db.execute_statement(sql_statement)
            for task in self.get_currently_running_tasks():
                if task.statusid == 7:
                    self._logger.debug(f"Setting 'Not Schedled' task '{task.taskname}' to currently running and setting status to 'Not Started'.")
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
                    self._logger.debug(f"Updating 'Not Schedled' task '{task.taskname}' to due date {task.duedate} and setting status to 'Not Started'.")
                    sql_statement = f"UPDATE tblTask SET StatusID = 1, DueDate = '{task.duedate}', ScheduledDueDate = '{task.scheduledduedate}', UpdateUserID = '{self._automated_user_id}', UpdatedTimestamp = CURRENT_TIMESTAMP WHERE ID = {task.task_id}"
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
                else:
                    self._logger.debug(f"Updating task '{task.taskname}' to due date {task.duedate}.")
                    sql_statement = f"UPDATE tblTask SET DueDate = '{task.duedate}', ScheduledDueDate = '{task.scheduledduedate}', UpdateUserID = '{self._automated_user_id}', UpdatedTimestamp = CURRENT_TIMESTAMP WHERE ID = {task.task_id}"
                    try:
                        db.execute_statement(sql_statement)
                    except Exception as e:
                        self._logger.error(f"Database error while updating Task Record. SQL statement: {sql_statement}")
