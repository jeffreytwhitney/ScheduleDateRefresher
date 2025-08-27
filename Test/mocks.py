import csv
import os
from typing import List

import dateutil.parser

from ImportRecords import ImportRecord
from TaskIDLinkRecords import TaskIDLinkRecord
from TaskNameLinkRecords import TaskNameLinkRecord
from Tasks import Task


class FakeRun:
    def __init__(self, site_id):
        self.site_id = site_id
        self.schedule_run_id = 123
        self.is_runnable = True

    def start_run(self): pass

    def complete_run(self, error_count, updated_count): pass


class FakeTaskIDLinkWriter:
    _task_id_link_records: List[TaskIDLinkRecord] = []

    def __init__(self, site_id):
        self.site_id = site_id

    def add_task_id_link_record(self, task_id, linked_table_name_id, machine_name):
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_id_link_records.append(TaskIDLinkRecord(task_id, linked_table_name_id, machine_name))

    def write_task_id_link_records_to_database(self): pass


class FakeTaskWriter:
    def __init__(self, site_id: int):
        site_id = site_id

    def _get_tasks(self) -> List[Task]:
        current_dir = os.path.dirname(__file__)
        tasks_file = f"{current_dir}\\tasks.csv"
        tasks = []
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task = Task(
                        int(row['ID']),
                        int(row['ProjectID']),
                        int(row['StatusID']),
                        row['TaskName'],
                        dateutil.parser.parse(row['DueDate']),
                        dateutil.parser.parse(row['ScheduledDueDate'])
                    )
                    tasks.append(task)
        return tasks

    def update_db_auto_not_scheduled(self):
        pass

    def write_currently_running_tasks_to_database(self):
        pass

    def write_updated_tasks_to_database(self):
        pass


class FakeTaskNameLinkWriter:

    def __init__(self, site_id):
        self._task_name_link_records: List[TaskNameLinkRecord] = []
        self.site_id = site_id

    def write_task_name_link_records_to_database(self): pass

    @property
    def task_name_link_records(self):
        return self._task_name_link_records

    def add_task_name_link_record(self, task_name, linked_table_name_id, machine_name, currently_running):
        task_name = task_name.replace("\"", "").replace("'", "")
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_name_link_records.append(TaskNameLinkRecord(task_name, linked_table_name_id, machine_name, currently_running))


class FakeImportRecordWriter:
    def __init__(self, site_id):
        self._import_records: List[ImportRecord] = []
        self.site_id = site_id

    def write_import_records_to_database(self): pass

    @property
    def import_records(self):
        return self._import_records

    def add_import_record(self, task_name, due_date):
        self._import_records.append(ImportRecord(task_name, due_date))
