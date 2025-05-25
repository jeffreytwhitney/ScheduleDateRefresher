import os
from datetime import datetime, timedelta

import xlwings
from dateutil import parser

from ScheduleInfo import ScheduleInfo


class ScheduleFileNotFoundError(Exception):
    pass


class ScheduleBadHeadersError(Exception):
    pass


def _is_parsable_date(date_string):
    try:
        parser.parse(date_string)
        return True
    except ValueError:
        return False


class Schedule:
    _schedule_info: ScheduleInfo
    _excel_application: xlwings.App
    _workbook: xlwings.Book
    _sheet: xlwings.Sheet
    _partnumber_cell: xlwings.Range
    _completion_date_cell: xlwings.Range
    _used_range: xlwings.Range
    _valid_part_delimiters = []
    _machine_name: str
    _min_completion_date: datetime = datetime.now() - timedelta(days=365)

    def __init__(self, schedule_config: ScheduleInfo):
        self._schedule_info = schedule_config
        self._load_schedule()

    def __exit__(self):
        self._workbook.close()
        self._excel_application.quit()

    def _load_schedule(self):
        filepath = self._schedule_info.file_path
        sheetname = self._schedule_info.sheet_name
        partnumber_address = self._schedule_info.starting_cell_address
        completion_offset = self._schedule_info.completion_date_cell_offset
        _valid_part_delimiters = self._schedule_info.task_name_delimiter.split(', ')

        if not os.path.isfile(filepath):
            raise ScheduleFileNotFoundError(self._schedule_info.file_path)

        xlapp = xlwings.App(visible=False)
        xlbook = xlwings.Book(filepath)
        xlsheet = xlbook.sheets[sheetname]
        xlpartRange = xlsheet.range(partnumber_address)
        xlcompletionRange = xlpartRange.offset(0, completion_offset)
        self._excel_application = xlapp
        self._workbook = xlbook
        self._sheet = xlsheet
        self._partnumber_cell = xlpartRange
        self._completion_date_cell = xlcompletionRange
        self._used_range = xlsheet.used_range
        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            self._machine_name = machine_name_cell.value
        else:
            raise ScheduleBadHeadersError(self._schedule_info.file_path)

    @property
    def partnumber_value(self) -> str:
        if self._partnumber_cell.value is None:
            return ""
        if self._schedule_info.do_part_name_trimming:
            return self._partnumber_cell.value.split(' ')[0].strip()

        return self._partnumber_cell.value

    @property
    def completion_date_value(self) -> str:
        if self._completion_date_cell.value is None:
            return ""

        return self._completion_date_cell.value

    @property
    def completion_datetime(self) -> datetime:
        return parser.parse(self.completion_date_value)

    @property
    def is_completion_date_valid(self) -> bool:
        return _is_parsable_date(self.completion_date_value) and parser.parse(self.completion_date_value) > self._min_completion_date

    @property
    def row_count(self) -> int:
        return self._used_range.rows.count

    @property
    def partnumber_cell(self):
        return self._partnumber_cell

    @property
    def completion_date_cell(self):
        return self._completion_date_cell

    @property
    def is_part_number_delimiter(self) -> bool:
        return self.partnumber_value in self._valid_part_delimiters

    @property
    def is_completion_date_delimiter(self) -> bool:
        return self.completion_date_value == self._schedule_info.completion_date_delimiter

    @property
    def machine_name(self) -> str:
        return self._machine_name

    @property
    def is_new_section(self) -> bool:
        return self.is_part_number_delimiter and self.is_completion_date_delimiter

    def offset(self):
        self._partnumber_cell = self._partnumber_cell.offset(1, 0)
        self._completion_date_cell = self._completion_date_cell.offset(1, 0)

        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            self._machine_name = machine_name_cell.value
