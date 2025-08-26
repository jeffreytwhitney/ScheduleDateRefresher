import builtins
import os
import sys
import types
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

import pytest

import Schedule


class FakeRange:
    def __init__(self, value=None, row=1):
        self.value = value
        self.row = row
        self._end_target = None
        self._offsets = {}  # (dr, dc) -> FakeRange

    def offset(self, dr, dc):
        # Return predefined offset if exists; otherwise return a generic new range
        return self._offsets.get((dr, dc), FakeRange(None, self.row + dr))

    def set_offset(self, dr, dc, rng):
        self._offsets[(dr, dc)] = rng
        return rng

    def end(self, direction):
        # direction is a string like 'down' or 'up', but we just return target
        return self._end_target if self._end_target else self

    def set_end_target(self, rng):
        self._end_target = rng
        return rng


class FakeSheet:
    def __init__(self, starting_cell_addr, start_range: FakeRange, final_row_value: int):
        # used_range.rows.count is used to compute row_count
        self.used_range = SimpleNamespace(rows=SimpleNamespace(count=final_row_value))
        self._starting_cell_addr = starting_cell_addr
        self._start_range = start_range
        self._final_row_value = final_row_value

    def range(self, addr):
        # If asking for the starting cell, return the provided start range
        if addr == self._starting_cell_addr:
            return self._start_range
        # If asking for the computed used_range_address (like 'A20'), return a range whose end('up').row = final_row_value
        # We return a FakeRange whose end('up') returns a FakeRange with .row = _final_row_value
        r = FakeRange(row=self._final_row_value)
        return FakeRange().set_end_target(r)


def get_current_directory():
    if getattr(sys, 'frozen', False):  # Check if running as an executable
        return os.path.dirname(sys.executable)
    else:  # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def make_schedule_info(file_name: str):
    current_directory = get_current_directory()
    file_path = os.path.join(current_directory, file_name)
    schedule_info = Schedule.ScheduleInfo(1, True, 1, 'Ortho Mill Dept 1', file_path,
                                          "Schedule", "D6", 23, -3, -2, "PART #", "COMP DATE", 1)
    return schedule_info


def test_get_alpha_portion():
    assert Schedule._get_alpha_portion("A1B2C3") == "ABC"
    assert Schedule._get_alpha_portion("123") == ""
    assert Schedule._get_alpha_portion("XyZ_99") == "XyZ"


@patch('Schedule.RefreshLogger.get_logger')
def test_load_schedule_file_not_found_raises(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(file_name="missing.xlsx")

    with pytest.raises(Schedule.ScheduleFileNotFoundError):
        Schedule.Schedule(info)
    assert mock_logger.error.called


@patch('Schedule.RefreshLogger.get_logger')
def test_load_schedule(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(file_name="OrthoMill1.xlsx")
    schedule = Schedule.Schedule(info)
    assert schedule.is_new_section




# def test_load_schedule_bad_headers_raises_and_cleans_up():
#     info = make_schedule_info(
#         task_name_delimiter="TASK",
#         completion_date_delimiter="DATE",
#     )
#
#     # Start cell values that DO NOT match both delimiters simultaneously to force bad headers
#     start = FakeRange(value="NOT_TASK")
#     completion = FakeRange(value="NOT_DATE")
#     # connect offsets: completion offset is +1 column
#     start.set_offset(0, info.completion_date_cell_offset, completion)
#
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=10)
#
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         # Ensure xlwings.Book(...) returns fake_book
#         Schedule.xlwings.Book.return_value = fake_book
#         # Accessing sheet.range happens on our FakeSheet
#         with pytest.raises(Schedule.ScheduleBadHeadersError):
#             Schedule.Schedule(info)
#         # Should close workbook and quit app on bad headers
#         fake_book.close.assert_called()
#         fake_app.quit.assert_called()
#
#
# def test_initialization_success_sets_machine_name_and_row_count():
#     info = make_schedule_info(
#         task_name_delimiter="TASK",            # part delimiter
#         completion_date_delimiter="DATE",      # completion delimiter
#         machine_name_offset_left=-1,
#         machine_name_offset_up=-1,
#     )
#
#     start = FakeRange(value="TASK", row=1)
#     completion = FakeRange(value="DATE", row=1)
#     machine_cell = FakeRange(value="MACHINE-01", row=0)  # at (-1, -1) from start
#
#     start.set_offset(0, info.completion_date_cell_offset, completion)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine_cell)
#
#     final_row_value = 25  # used to compute row_count
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=final_row_value)
#
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             assert s.machine_name == "MACHINE-01"
#             assert s.row_count == final_row_value
#         finally:
#             s.close()
#
#
# def test_partnumber_value_float_trims_dot_zero_and_trimming_behavior():
#     info = make_schedule_info(task_name_delimiter="TASK", completion_date_delimiter="DATE")
#     start = FakeRange(value="TASK")
#     completion = FakeRange(value="DATE")
#     start.set_offset(0, info.completion_date_cell_offset, completion)
#     machine = FakeRange(value="M", row=0)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine)
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=5)
#
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             # float with .0 should be trimmed
#             s._partnumber_cell.value = 123.0
#             assert s.partnumber_value == "123"
#
#             # trimming disabled: return raw (already "123")
#             s._partnumber_cell.value = "abc def"
#             assert s.partnumber_value == "abc def"
#
#             # enable trimming: should take first token and uppercase
#             s._schedule_info.do_part_name_trimming = True
#             assert s.partnumber_value == "ABC"
#         finally:
#             s.close()
#
#
# def test_completion_date_parsing_and_validity():
#     info = make_schedule_info(task_name_delimiter="TASK", completion_date_delimiter="DATE")
#     start = FakeRange(value="TASK")
#     completion = FakeRange(value="DATE")
#     start.set_offset(0, info.completion_date_cell_offset, completion)
#     machine = FakeRange(value="M", row=0)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine)
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=5)
#
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             # None completion -> empty value, min datetime, invalid
#             s._completion_date_cell.value = None
#             assert s.completion_date_value == ""
#             assert s.completion_datetime == datetime.min
#             assert not s.is_completion_date_valid
#
#             # Valid recent date
#             recent = datetime.now().strftime("%Y-%m-%d")
#             s._completion_date_cell.value = recent
#             assert s.completion_date_value == recent
#             assert s.completion_datetime.date().isoformat() == recent
#             assert s.is_completion_date_valid is True
#
#             # Old date beyond min (set min to tomorrow to force invalid)
#             s._min_completion_date = datetime.now() + timedelta(days=1)
#             assert s.is_completion_date_valid is False
#
#             # Invalid parseable string
#             s._completion_date_cell.value = "not-a-date"
#             assert s.completion_datetime == datetime.min
#             assert s.is_completion_date_valid is False
#         finally:
#             s.close()
#
#
# def test_is_at_end_uses_row_count():
#     info = make_schedule_info(task_name_delimiter="TASK", completion_date_delimiter="DATE")
#     start = FakeRange(value="TASK", row=9)
#     completion = FakeRange(value="DATE", row=9)
#     start.set_offset(0, info.completion_date_cell_offset, completion)
#     machine = FakeRange(value="M", row=8)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine)
#
#     final_row_value = 10
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=final_row_value)
#
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             s._row_count = 10
#             s._partnumber_cell.row = 9
#             assert s.is_at_end is False
#
#             s._partnumber_cell.row = 10
#             assert s.is_at_end is True
#         finally:
#             s.close()
#
#
# def test_get_next_row_updates_cells_and_sets_machine_unknown_when_none():
#     info = make_schedule_info(
#         task_name_delimiter="TASK",
#         completion_date_delimiter="DATE",
#         machine_name_offset_left=-1,
#         machine_name_offset_up=-1,
#         completion_date_cell_offset=1,
#     )
#     # First row (current)
#     start = FakeRange(value="TASK", row=1)
#     completion1 = FakeRange(value="DATE", row=1)
#     start.set_offset(0, info.completion_date_cell_offset, completion1)
#     machine1 = FakeRange(value="IGNORED", row=0)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine1)
#
#     # Next "down" row
#     next_part = FakeRange(value="TASK", row=5)
#     next_completion = FakeRange(value="DATE", row=5)
#     next_machine = FakeRange(value=None, row=4)  # None -> should become UNKNOWN
#     next_part.set_offset(0, info.completion_date_cell_offset, next_completion)
#     next_part.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, next_machine)
#
#     # Configure start.end('down') to return next_part
#     start.set_end_target(next_part)
#
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=20)
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             s.get_next_row()
#             assert s.partnumber_cell is next_part
#             assert s.completion_date_cell is next_completion
#             assert s.machine_name == "UNKNOWN"
#         finally:
#             s.close()
#
#
# def test_offset_uses_second_chance_for_machine_name():
#     info = make_schedule_info(
#         task_name_delimiter="TASK",
#         completion_date_delimiter="DATE",
#         machine_name_offset_left=-1,
#         machine_name_offset_up=-1,
#         completion_date_cell_offset=1,
#     )
#     # Current row is a delimiter row
#     start = FakeRange(value="TASK", row=1)
#     completion1 = FakeRange(value="DATE", row=1)
#     start.set_offset(0, info.completion_date_cell_offset, completion1)
#
#     # Machine at (-1,-1) from current is None
#     machine_current = FakeRange(value=None, row=0)
#     start.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine_current)
#
#     # After offset by +1 row, new part/completion (still delimiter row)
#     next_part = FakeRange(value="TASK", row=2)
#     next_completion = FakeRange(value="DATE", row=2)
#     # Hook the offset methods to return the next cells
#     start.set_offset(1, 0, next_part)
#     completion1.set_offset(1, 0, next_completion)
#
#     # For the new row, machine at (-1,-1) is None, but the "second chance" cell (offset(1,0)) has value
#     machine_new_primary = FakeRange(value=None, row=1)
#     machine_new_second = FakeRange(value="MACHINE-SECOND", row=2)
#     next_part.set_offset(info.machine_name_offset_up, info.machine_name_offset_left, machine_new_primary)
#     # machine_new_primary.offset(1,0) should return machine_new_second
#     machine_new_primary.set_offset(1, 0, machine_new_second)
#
#     sheet = FakeSheet(info.starting_cell_address, start, final_row_value=10)
#     app_patcher, book_patcher, fake_app, fake_book = setup_xlwings_mocks(start, sheet)
#     with app_patcher, book_patcher, patch("os.path.isfile", return_value=True):
#         s = Schedule.Schedule(info)
#         try:
#             s.offset()
#             assert s.partnumber_cell is next_part
#             assert s.completion_date_cell is next_completion
#             assert s.machine_name == "MACHINE-SECOND"
#         finally:
#             s.close()
