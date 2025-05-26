from datetime import datetime, timedelta
from typing import List

import DB


def prev_weekday(adate):
    adate -= timedelta(days=1)
    while adate.weekday() > 4:  # Mon-Fri are 0-4
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
            duedate=record['DueDate'],
            scheduledduedate=record['ScheduledDueDate']
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

    def get_tasks_by_name(self, task_name: str) -> List[Task]:
        return [task for task in self._tasks if task.taskname == task_name]

    def get_updated_tasks(self) -> List[Task]:
        return [task for task in self._tasks if task.is_updated]

    def update_dates_by_taskname(self, task_name: str, due_date: datetime) -> None:
        tasks = self.get_tasks_by_name(task_name)
        for task in tasks:
            task._duedate = due_date
            task._scheduledduedate = prev_weekday(due_date)
            task._updated = True
            if task.statusid == 7:
                task._statusid = 1

    def write_updated_tasks_to_database(self) -> None:

        for task in self.get_updated_tasks():
            if task.is_updated:

                if task.statusid == 7:
                    sql_statement = "UPDATE tblTask SET DueDate = '{due_date}', ScheduledDueDate = '{scheduledduedate}' "
                    "WHERE ID = {task_id}".format(
                        due_date=task.duedate,
                        scheduledduedate=task.scheduledduedate,
                        task_id=task.task_id
                    )
                else:
                    sql_statement = "UPDATE tblTask SET StatusID = 1, DueDate = '{due_date}', ScheduledDueDate = '{scheduledduedate}' "
                    "WHERE ID = {task_id}".format(
                        due_date=task.duedate,
                        scheduledduedate=task.scheduledduedate,
                        task_id=task.task_id
                    )

                try:
                    DB.execute_sql_statement(sql_statement)
                except:
                    pass
