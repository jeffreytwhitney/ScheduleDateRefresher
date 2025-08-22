from datetime import datetime

from Schedule import Schedule
from ImportRecords import ImportRecordWriter
from ScheduleRun import ScheduleRun
from TaskNameLinkRecords import TaskNameLinkRecordWriter
import logging.config
import Lib


class ScheduleProcessor:
    """Schedule Processor:
    Processes schedules, updates task records, and manages import records.

    The class is responsible for iterating through a schedule, handling task name
    and completion date processing, and interacting with external components to
    manage task record links and import records. It processes rows of schedule data,
    validates completion dates, and updates necessary records based on the data provided.

    :ivar site_id: Identifier for the site associated with this schedule processor.
    :type site_id: int
    """
    _schedule_run: ScheduleRun
    _schedule: Schedule
    _import_record_writer: ImportRecordWriter
    _previous_task_name: str = ""
    _previous_completion_date: datetime = datetime.min
    _current_completion_date: datetime = datetime.min
    _site_id: int = 0
    _task_name_link_record_writer: TaskNameLinkRecordWriter
    _machine_name: str = ""
    _import_records: ImportRecordWriter
    _current_task_name: str = ""
    _logger: logging.Logger

    def __init__(self, site_id: int, schedule_run: ScheduleRun, schedule: Schedule, import_record_writer: ImportRecordWriter, task_name_link_record_writer: TaskNameLinkRecordWriter):
        conf_path = Lib.get_current_directory() + "\\logging.conf"
        logging.config.fileConfig(conf_path)
        self._logger = logging.getLogger('scheduleProcessorLogger')
        self._schedule_run = schedule_run
        self._schedule = schedule
        self._import_record_writer = import_record_writer
        self._task_name_link_record_writer = task_name_link_record_writer
        self._site_id = site_id

    def process_schedule(self):
        """
        Processes a schedule to generate task name link records and import records.

        The `process_schedule` method performs a detailed traversal and processing
        of schedule data contained within the `_schedule` object. It updates task
        name link records as well as import records based on the data provided in
        the schedule. The method handles tasks, offsets empty or invalid rows, and
        logs critical information during its execution.

        Raised exceptions, parameters, and returns are described in their respective sections.

        :raises AttributeError: If any required object or attribute is missing
            within the context of this method.
        :raises ValueError: If the schedule data contains unexpected or invalid information.
        :return: None
        """
        self._logger.debug(f"Processing Schedule ID: {self._schedule.schedule_id}")
        self._previous_task_name: str = ""
        self._previous_completion_date: datetime = datetime.min
        self._current_completion_date: datetime = datetime.min

        self._machine_name: str = ""

        for _ in range(1, self._schedule.row_count - 1):
            if self._schedule.is_new_section:
                self._previous_task_name = ""
                self._previous_completion_date = datetime.min
                self._machine_name = self._schedule.machine_name.replace("\"", "").replace("'", "")
                self._schedule.offset()
                continue

            if self._schedule.partnumber_value == '':
                # I'm calling offset() here instead of offset so that I can skip a bunch of empty rows.
                self._schedule.get_next_row()
                if self._schedule.is_at_end:
                    break
                continue

            if self._schedule.completion_date_value == '':
                self._schedule.offset()
                continue

            if not self._schedule.is_completion_date_valid:
                self._schedule.offset()
                continue

            self._current_task_name = str(self._schedule.partnumber_value).replace("\"", "").replace("'", "")

            if self._current_task_name == 'C20921-15':
                # This is just for testing so that I can set a break point on a particular task name
                pass

            self._current_completion_date = self._schedule.completion_datetime
            if self._previous_task_name == self._current_task_name:
                self._schedule.offset()
                continue

            self._previous_task_name = self._current_task_name

            if self._previous_completion_date is not datetime.min:
                self._logger.debug(f"Updating Task Name Link Record (NOT CURRENTLY RUNNING) for Task: {self._current_task_name} on Schedule ID: {self._schedule.schedule_id} on Machine: {self._machine_name}")
                self._task_name_link_record_writer.add_task_name_link_record(self._current_task_name, self._schedule.schedule_id, self._machine_name, False)
            else:
                self._logger.debug(f"Updating Task Name Link Record (CURRENTLY RUNNING) for Task: {self._current_task_name} on Schedule ID: {self._schedule.schedule_id} on Machine: {self._machine_name}")
                self._task_name_link_record_writer.add_task_name_link_record(self._current_task_name, self._schedule.schedule_id, self._machine_name, True)

            if self._previous_completion_date is not datetime.min:
                self._logger.debug(f"Updating Import Record for Task: {self._current_task_name} with Due Date: {self._previous_completion_date}")
                self._import_record_writer.add_import_record(self._current_task_name, self._previous_completion_date)

            self._previous_completion_date = self._current_completion_date
            self._schedule.offset()
