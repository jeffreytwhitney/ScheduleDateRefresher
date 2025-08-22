import os
import logging.config
import dateutil
from dateutil.parser import parse
from datetime import datetime, timedelta
import Lib
import xlwings

from ScheduleInfo import ScheduleInfo


def _get_alpha_portion(s):
    return ''.join([char for char in s if char.isalpha()])


class ScheduleFileNotFoundError(Exception):
    pass


class ScheduleBadHeadersError(Exception):
    pass


class Schedule:
    """
    Encapsulates the operations and functionality related to managing a schedule-loaded
    Excel file with information such as part numbers, completion dates, and machine names.

    This class provides methods and properties to interact with the data stored in the Excel file,
    validate headers, extract information such as part numbers and machine names, and navigate
    through rows in the sheet.

    :ivar partnumber_value: The value of the part number in the currently active cell.
    :type partnumber_value: str
    :ivar schedule_id: The unique identifier for the schedule configuration.
    :type schedule_id: int
    :ivar completion_date_value: The value of the completion date in the currently active cell.
    :type completion_date_value: str
    :ivar completion_datetime: The parsed datetime object of the completion date in the active cell.
    :type completion_datetime: datetime
    :ivar is_completion_date_valid: Indicates whether the completion date is valid based on the minimum allowable date.
    :type is_completion_date_valid: bool
    :ivar row_count: The total number of rows in the used range of the sheet.
    :type row_count: int
    :ivar partnumber_cell: Represents the current cell associated with the part number.
    :type partnumber_cell: xlwings.Range
    :ivar completion_date_cell: Represents the current cell associated with the completion date.
    :type completion_date_cell: xlwings.Range
    :ivar is_part_number_delimiter: Indicates whether the current part number cell matches a valid part number delimiter.
    :type is_part_number_delimiter: bool
    :ivar is_completion_date_delimiter: Indicates whether the current completion date cell matches the delimiter.
    :type is_completion_date_delimiter: bool
    :ivar machine_name: The name of the machine corresponding to the current part section.
    :type machine_name: str
    :ivar is_new_section: Indicates whether the current row is the start of a new schedule section.
    :type is_new_section: bool
    :ivar is_at_end: Indicates whether the last processed part number cell is at or beyond the row count.
    :type is_at_end: bool
    """
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
    _logger: logging.Logger

    def __init__(self, schedule_config: ScheduleInfo) -> None:
        conf_path = Lib.get_current_directory() + "\\logging.conf"
        logging.config.fileConfig(conf_path)
        self._logger = logging.getLogger('scheduleLogger')
        self._schedule_info = schedule_config
        self._load_schedule()

    def close(self) -> None:
        self._logger.debug("Closing Schedule")
        if self._workbook:
            self._workbook.close()
        if self._excel_application:
            self._excel_application.quit()

    def _load_schedule(self) -> None:
        """
        Processes and loads schedule data from an Excel file using xlwings, initializes
        necessary objects, and validates the schedule's format.

        This method loads schedule information such as the workbook, worksheet, specified
        cell ranges for part numbers and completion dates, and other required attributes
        from the schedule file. It also validates the headers in the schedule to ensure
        correctness before processing. If the file is not found or the headers are invalid,
        specific errors are raised.

        :param self: The instance of the class calling the method.

        :raises ScheduleFileNotFoundError: If the schedule file does not exist at the
            specified file path.
        :raises ScheduleBadHeadersError: If the headers of the schedule file do not follow
            the expected format.
        """
        self._logger.debug(f"Loading Schedule:{self._schedule_info.import_name}")
        xlapp = xlwings.App(visible=False)
        self._excel_application = xlapp
        filepath = self._schedule_info.file_path
        sheetname = self._schedule_info.sheet_name
        partnumber_address = self._schedule_info.starting_cell_address
        completion_offset = self._schedule_info.completion_date_cell_offset
        self._valid_part_delimiters = self._schedule_info.task_name_delimiter.upper().split(', ')

        if not os.path.isfile(filepath):
            self._logger.error(f"Schedule File Not Found:{filepath}")
            raise ScheduleFileNotFoundError(self._schedule_info.file_path)

        xlbook = xlwings.Book(filepath, update_links=False, read_only=True)
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
            self._logger.error(f"Bad Headers in Schedule:{filepath}")
            if self._workbook:
                self._workbook.close()
            if self._excel_application:
                self._excel_application.quit()
            raise ScheduleBadHeadersError(self._schedule_info.file_path)

    @property
    def partnumber_value(self) -> str:
        """
        Computes and retrieves the processed part number value based on the rules defined
        in the method. The method processes the raw part number value from a source and
        applies transformations such as trimming, type handling, and other adjustments.

        :rtype: str
        :returns: The processed part number value. If the source value is None, an
                  empty string is returned. If trimming is enabled (via
                  `do_part_name_trimming` in `schedule_info`), the part number is
                  trimmed to the first segment of its value, converted to uppercase, and
                  stripped of leading/trailing spaces.
        """
        part_number_value = str(self._partnumber_cell.value)
        if isinstance(self._partnumber_cell.value, float):
            if part_number_value.endswith(".0"):
                part_number_value = part_number_value[:-2]

        if self._partnumber_cell.value is None:
            return ""
        if self._schedule_info.do_part_name_trimming:
            return part_number_value.split(' ')[0].upper().strip()

        return part_number_value

    @property
    def schedule_id(self) -> int:
        return self._schedule_info.schedule_id

    @property
    def completion_date_value(self) -> str:
        if self._completion_date_cell.value is None:
            return ""

        return str(self._completion_date_cell.value)

    @property
    def completion_datetime(self) -> datetime:
        try:
            return dateutil.parser.parse(self.completion_date_value)
        except ParserError:
            return datetime.min

    @property
    def is_completion_date_valid(self) -> bool:
        try:
            completion_date = dateutil.parser.parse(self.completion_date_value)
        except dateutil.parser.ParserError:
            return False
        return completion_date > self._min_completion_date

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
        """
        Determines the next row of part number and corresponding completion date
        and updates the internal tracking state for the machine name based on the
        defined offsets. It calculates the location of relevant cells and retrieves
        data accordingly, interpreting empty machine name cells as "UNKNOWN".

        :raises AttributeError: If any required attributes or methods are missing
            for the calculations (e.g., ``_schedule_info`` attributes are not defined properly).
        """
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
        """
        Adjusts the offset of certain cells by shifting them vertically and checks for machine name presence
        based on their new positions. The function updates `_machine_name` depending on the presence of a
        valid value in the expected cell or its alternative location.

        :raises AttributeError: If accessed, attributes or methods are not available during execution.
        """
        self._partnumber_cell = self._partnumber_cell.offset(1, 0)
        self._completion_date_cell = self._completion_date_cell.offset(1, 0)

        if self.is_part_number_delimiter and self.is_completion_date_delimiter:
            machine_offset_left = int(self._schedule_info.machine_name_offset_left)
            machine_offset_up = int(self._schedule_info.machine_name_offset_up)
            machine_name_cell = self._partnumber_cell.offset(machine_offset_up, machine_offset_left)
            if machine_name_cell.value is None:
                machine_name_second_chance = machine_name_cell.offset(1, 0)
                if machine_name_second_chance.value is None:
                    self._machine_name = "UNKNOWN"
                else:
                    self._machine_name = str(machine_name_second_chance.value)
            else:
                self._machine_name = str(machine_name_cell.value)
