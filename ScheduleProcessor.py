import datetime

import Schedule
from ImportRecords import ImportRecordWriter
from ScheduleRun import ScheduleRun
from TaskNameLinkRecords import TaskNameLinkRecordWriter


class ScheduleProcessor:
    _schedule_run: ScheduleRun = None
    _schedule: Schedule = None
    _import_record_writer: ImportRecordWriter = None

    def __init__(self, site_id: int, schedule_run: ScheduleRun, schedule: Schedule, import_record_writer: ImportRecordWriter, task_name_link_record_writer: TaskNameLinkRecordWriter):
        self._schedule_run = schedule_run
        self._schedule = schedule
        self._import_record_writer = import_record_writer
        self._task_name_link_record_writer = task_name_link_record_writer
        self._site_id = site_id

    def process_schedule(self):
        previous_task_name: str = ""
        previous_completion_date: datetime = None
        machine_name: str = ""

        for _ in range(1, self._schedule.row_count):
            if self._schedule.is_new_section:
                previous_task_name = ""
                previous_completion_date = None
                machine_name = self._schedule.machine_name_value
                self._schedule.offset()
                continue

            if self._schedule.partnumber_value == '' or self._schedule.completion_date_value == '':
                self._schedule.offset()
                continue
            if not self._schedule.is_completion_date_valid:
                self._schedule.offset()
                continue

            current_task_name = self._schedule.partnumber_value
            current_completion_date = self._schedule.completion_datetime

            if previous_task_name == current_task_name:
                continue

            previous_task_name = current_task_name

            self._task_name_link_record_writer.add_task_name_link_record(current_task_name, self._schedule.linked_table_name_id, machine_name)

            if previous_completion_date is not None:
                self._import_record_writer.add_import_record(current_task_name, previous_completion_date)

            previous_completion_date = current_completion_date
            self._schedule.offset()
