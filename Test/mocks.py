import csv
import os
import sys
from datetime import datetime, timedelta
from typing import List

import dateutil.parser

from ImportRecords import ImportRecord
from ScheduleInfo import ScheduleInfo
from TaskIDLinkRecords import TaskIDLinkRecord
from TaskNameLinkRecords import TaskNameLinkRecord
from Tasks import Task


def prev_weekday(adate):
    adate -= timedelta(days=1)
    while adate.weekday() > 4:
        adate -= timedelta(days=1)
    return adate


def get_current_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def get_tasks(self) -> List[Task]:
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


def make_schedule_info(schedule_id: int, is_active: bool, site_id: int, import_name: str, file_name: str
                       , sheet_name: str, starting_cell_address: str, completion_date_cell_offset: int,
                       machine_name_offset_left: int, machine_name_offset_up: int, task_name_delimiter: str,
                       completion_date_delimiter: str, do_part_name_trimming: bool) -> ScheduleInfo:
    current_directory = get_current_directory()
    file_path = os.path.join(current_directory, file_name)
    schedule_info = ScheduleInfo(schedule_id, is_active, site_id, import_name, file_path,
                                 sheet_name, starting_cell_address, completion_date_cell_offset,
                                 machine_name_offset_left, machine_name_offset_up, task_name_delimiter,
                                 completion_date_delimiter, do_part_name_trimming)
    return schedule_info


def get_schedule_info_records(site_id: int) -> List[ScheduleInfo]:
    return [make_schedule_info(1, True, site_id, "Ortho Mill Dept 1", "OrthoMill1.xlsx",
                               "Schedule", "D6", 23, -3, -2, "#, PART #", "COMP DATE", True)]


def fake_ini(section, key, app):
    if (section, key) == ("Site", "site"):
        return "1"
    if (section, key) == ("Switches", "auto_not_scheduled"):
        return "0"
    if (section, key) == ("Switches", "run_local"):
        return "0"
    return "0"


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

    @property
    def task_id_link_records(self):
        return self._task_id_link_records

    def add_task_id_link_record(self, task_id, linked_table_name_id, machine_name):
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_id_link_records.append(TaskIDLinkRecord(task_id, linked_table_name_id, machine_name))

    def write_task_id_link_records_to_database(self): pass


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


class FakeLogger:
    def debug(self, *a, **k): pass
    def info(self, *a, **k): pass
    def error(self, *a, **k): pass
