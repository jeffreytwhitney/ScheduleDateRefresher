import datetime
import os
import sys

from unittest.mock import patch, MagicMock

import pytest

import Schedule


def get_current_directory():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


def make_schedule_info(schedule_id: int, is_active: bool, site_id: int, import_name: str, file_name: str
                       , sheet_name: str, starting_cell_address: str, completion_date_cell_offset: int,
                       machine_name_offset_left: int, machine_name_offset_up: int, task_name_delimiter: str,
                       completion_date_delimiter: str, do_part_name_trimming: bool):
    current_directory = get_current_directory()
    file_path = os.path.join(current_directory, file_name)
    schedule_info = Schedule.ScheduleInfo(schedule_id, is_active, site_id, import_name, file_path,
                                          sheet_name, starting_cell_address, completion_date_cell_offset,
                                          machine_name_offset_left, machine_name_offset_up, task_name_delimiter,
                                          completion_date_delimiter, do_part_name_trimming)
    return schedule_info


def test_get_alpha_portion():
    assert Schedule._get_alpha_portion("A1B2C3") == "ABC"
    assert Schedule._get_alpha_portion("123") == ""
    assert Schedule._get_alpha_portion("XyZ_99") == "XyZ"


@patch('Schedule.RefreshLogger.get_logger')
def test_load_schedule_file_not_found_raises(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Sheet1', file_name="missing.xlsx",
                              sheet_name="Sheet1", starting_cell_address="A1", completion_date_cell_offset=1,
                              machine_name_offset_left=-1, machine_name_offset_up=-1, task_name_delimiter="TASK",
                              completion_date_delimiter="DATE", do_part_name_trimming=False)

    with pytest.raises(Schedule.ScheduleFileNotFoundError):
        Schedule.Schedule(info)
    assert mock_logger.error.called


@patch('Schedule.RefreshLogger.get_logger')
def test_load_schedule(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D6", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="#, PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.is_new_section
        assert schedule.row_count == 3137
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_load_schedule_bad_headers_raises_and_cleans_up(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D6", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="#",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)

    with pytest.raises(Schedule.ScheduleBadHeadersError):
        Schedule.Schedule(info)


@patch('Schedule.RefreshLogger.get_logger')
def test_initialization_success_sets_machine_name_and_row_count(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D6", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.machine_name == "CELL 1 (ROBO-01A/01B)"
        assert schedule.row_count == 3137
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "42517451010"
        assert schedule.schedule_id == 1
        formatted_date_string = datetime.date.today().strftime("%Y-%m-%d %H:%M:%S")
        assert schedule.completion_date_value == formatted_date_string
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_partnumber_trimming_and_partnumber_float_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D6", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.machine_name == "CELL 1 (ROBO-01A/01B)"
        assert schedule.row_count == 3137
        schedule.offset()
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "42517450710"
        schedule.offset()
        assert schedule.partnumber_value == "42527450810"
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_get_next_row_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D157", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.machine_name == "CELL 2 (ROBO-02A/02B)"
        assert schedule.row_count == 3137
        schedule.offset()
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "42517650910"
        schedule.get_next_row()
        assert schedule.is_new_section
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "42517050313"
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_is_completion_date_valid_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D263", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.machine_name == "CELL 3 (ROBO-03A/03B)"
        assert schedule.row_count == 3137
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "42517050313"
        assert schedule.is_completion_date_valid is False

    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_second_chance_machine_name_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D2227", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        assert schedule.machine_name == "MIKRON-01"
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_completion_date_too_early_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D2647", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        schedule.offset()
        assert schedule.partnumber_value == "123456798-009"
        assert schedule.is_completion_date_valid is False
    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_machine_set_to_unknown_behavior(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D1911", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    try:
        # Testing when first opening the schedule.
        assert schedule.is_new_section is True
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "110029095-00"
        assert schedule.is_completion_date_valid is True
        assert schedule.machine_name == "UNKNOWN"

        # Moving to the next section, does offset() function set machine_name to "UNKNOWN"
        schedule.offset()
        schedule.offset()
        schedule.offset()
        schedule.offset()
        schedule.offset()
        assert schedule.is_new_section is True
        assert schedule.machine_name == "UNKNOWN"
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "110029098-00"

        # Moving to the next section, does get_next_row() function set machine_name to "UNKNOWN"
        schedule.get_next_row()
        assert schedule.is_new_section is True
        assert schedule.machine_name == "UNKNOWN"
        schedule.offset()
        schedule.offset()
        assert schedule.partnumber_value == "110029099-00"

    finally:
        schedule.close()


@patch('Schedule.RefreshLogger.get_logger')
def test_is_at_end_uses_row_count(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    info = make_schedule_info(schedule_id=1, is_active=True, site_id=1, import_name='Ortho Mill Dept 1', file_name="OrthoMill1.xlsx",
                              sheet_name="Schedule", starting_cell_address="D3032", completion_date_cell_offset=23,
                              machine_name_offset_left=-3, machine_name_offset_up=-2, task_name_delimiter="PART #",
                              completion_date_delimiter="COMP DATE", do_part_name_trimming=True)
    schedule = Schedule.Schedule(info)
    assert schedule.is_new_section is True
    schedule.offset()
    schedule.get_next_row()
    assert schedule.is_at_end is True

