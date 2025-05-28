import os
from datetime import datetime, timedelta

import xlwings

from ScheduleInfo import ScheduleInfo

def _get_alpha_portion(s):
    return ''.join([char for char in s if char.isalpha()])


class ScheduleFileNotFoundError(Exception):
    pass


class ScheduleBadHeadersError(Exception):
    pass


class Schedule:
    _schedule_info: ScheduleInfo
    _excel_application: xlwings.App
    _workbook: xlwings.Book
    _sheet: xlwings.Sheet
    _partnumber_cell: xlwings.Range
    _completion_date_cell: xlwings.Range
    _used_range: xlwings.Range
    _row_count: int = 0
    _valid_part_delimiters = []
    _machine_name: str
    _min_completion_date: datetime = datetime.now() - timedelta(days=365)

    def __init__(self, schedule_config: ScheduleInfo):
        self._schedule_info = schedule_config
        self._load_schedule()

    def close(self):
        if self._workbook:
            self._workbook.close()
        if self._excel_application:
            self._excel_application.quit()

    def _load_schedule(self):
        xlapp = xlwings.App(visible=False)
        self._excel_application = xlapp
        filepath = self._schedule_info.file_path
        sheetname = self._schedule_info.sheet_name
        partnumber_address = self._schedule_info.starting_cell_address
        completion_offset = self._schedule_info.completion_date_cell_offset
        self._valid_part_delimiters = self._schedule_info.task_name_delimiter.upper().split(', ')

        if not os.path.isfile(filepath):
            raise ScheduleFileNotFoundError(self._schedule_info.file_path)

        xlbook = xlwings.Book(filepath)
        xlsheet = xlbook.sheets[sheetname]
        xlpartRange = xlsheet.range(partnumber_address)
        xlcompletionRange = xlpartRange.offset(0, completion_offset)

        self._workbook = xlbook
        self._sheet = xlsheet
        self._partnumber_cell = xlpartRange
        self._completion_date_cell = xlcompletionRange
        self._used_range = xlsheet.used_range

        rowcount = xlsheet.used_range.rows.count
        rowname_alpha = _get_alpha_portion(self._schedule_info.starting_cell_address)
        used_range_address = rowname_alpha + str(rowcount)
        self._row_count = xlsheet.range(used_range_address).end('up').row

        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            self._machine_name = machine_name_cell.value
        else:
            if self._workbook:
                self._workbook.close()
            if self._excel_application:
                self._excel_application.quit()
            raise ScheduleBadHeadersError(self._schedule_info.file_path)

    @property
    def partnumber_value(self) -> str:
        part_number_value = str(self._partnumber_cell.value)

        if self._partnumber_cell.value is None:
            return ""
        if self._schedule_info.do_part_name_trimming:
            return part_number_value.split(' ')[0].upper().strip()

        return part_number_value

    @property
    def schedule_id(self):
        return self._schedule_info.schedule_id

    @property
    def completion_date_value(self):
        if self._completion_date_cell.value is None:
            return ""

        return self._completion_date_cell.value

    @property
    def completion_datetime(self):
        if not isinstance(self.completion_date_value, datetime):
            return None
        return self.completion_date_value

    @property
    def is_completion_date_valid(self) -> bool:

        if not isinstance(self.completion_date_value, datetime):
            return False

        return self.completion_date_value > self._min_completion_date

    @property
    def row_count(self) -> int:
        return self._row_count

    @property
    def partnumber_cell(self):
        return self._partnumber_cell

    @property
    def completion_date_cell(self):
        return self._completion_date_cell

    @property
    def is_part_number_delimiter(self) -> bool:
        part_number_value = str(self._partnumber_cell.value).upper().strip()
        return part_number_value in self._valid_part_delimiters

    @property
    def is_completion_date_delimiter(self) -> bool:
        return self.completion_date_value.upper() == self._schedule_info.completion_date_delimiter.upper()

    @property
    def machine_name(self) -> str:
        return str(self._machine_name)

    @property
    def is_new_section(self) -> bool:
        return self.is_part_number_delimiter and self.is_completion_date_delimiter

    @property
    def is_at_end(self) -> bool:
        return self._partnumber_cell.row >= self._row_count

    def get_next_row(self):
        self._partnumber_cell = self._partnumber_cell.end('down')
        self._completion_date_cell = self._partnumber_cell.offset(0, self._schedule_info.completion_date_cell_offset)
        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            if machine_name_cell.value is None:
                self._machine_name = "UNKNOWN"
            else:
                self._machine_name = machine_name_cell.value

    def offset(self):
        self._partnumber_cell = self._partnumber_cell.offset(1, 0)
        self._completion_date_cell = self._completion_date_cell.offset(1, 0)

        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            if machine_name_cell.value is None:
                self._machine_name = "UNKNOWN"
            else:
                self._machine_name = machine_name_cell.value
