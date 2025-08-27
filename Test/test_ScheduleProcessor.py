import os
import sys
import types
from typing import List
from unittest.mock import patch, MagicMock

import pytest

import ScheduleDateRefresher
from ImportRecords import ImportRecordWriter

from ScheduleInfo import ScheduleInfo
from mocks import FakeTaskWriter
from mocks import FakeRun
from mocks import FakeTaskIDLinkWriter
from mocks import FakeTaskNameLinkWriter


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
    schedule_info = ScheduleInfo(schedule_id, is_active, site_id, import_name, file_path,
                                 sheet_name, starting_cell_address, completion_date_cell_offset,
                                 machine_name_offset_left, machine_name_offset_up, task_name_delimiter,
                                 completion_date_delimiter, do_part_name_trimming)
    return schedule_info


def get_schedule_info_records(site_id: int) -> List[ScheduleInfo]:
    return [make_schedule_info(1, True, site_id, "Ortho Mill Dept 1", "OrthoMill1.xlsx",
                               "Schedule", "D6", 23, -3, -2, "#, PART #", "COMP DATE", True)]


@pytest.fixture(autouse=True)
def isolate_env(monkeypatch):
    # Prevent Excel/OS operations
    monkeypatch.setattr(ScheduleDateRefresher, "_is_excel_running", lambda: False, raising=True)
    monkeypatch.setattr(ScheduleDateRefresher, "_force_close_excel", lambda: None, raising=True)

    # Stub psutil and win32com usage (if any path touches them)
    class _DummyProc:
        info = {"name": ""}

    monkeypatch.setattr("psutil.process_iter", lambda attrs=None: iter([_DummyProc()]), raising=False)
    try:
        import win32com.client as _w32
        monkeypatch.setattr(_w32, "Dispatch", lambda *_a, **_k: types.SimpleNamespace(Quit=lambda: None), raising=False)
    except Exception:
        pass

    # Stub INI values used by process_schedules
    def fake_ini(section, key, app):
        if (section, key) == ("Site", "site"):
            return "1"
        if (section, key) == ("Switches", "auto_not_scheduled"):
            return "0"
        if (section, key) == ("Switches", "run_local"):
            return "0"
        return "0"

    import INIConfig
    monkeypatch.setattr(INIConfig, "GetStoredIniValue", fake_ini, raising=True)

    # ScheduleRun stub: make it runnable but inert

    monkeypatch.setattr(ScheduleDateRefresher, "ScheduleRun", FakeRun, raising=True)

    import ScheduleInfo

    monkeypatch.setattr(ScheduleInfo, "get_schedule_info_records", lambda site_id: [], raising=True)

    # Monkeypatch ImportRecordWriter.write_import_records_to_database to be a no-op
    monkeypatch.setattr(ImportRecordWriter, "write_import_records_to_database", lambda self: None, raising=True)

    monkeypatch.setattr(ScheduleDateRefresher, "TaskNameLinkRecordWriter", FakeTaskNameLinkWriter, raising=True)
    monkeypatch.setattr(ScheduleDateRefresher, "TaskIDLinkRecordWriter", FakeTaskIDLinkWriter, raising=True)


@patch('Schedule.RefreshLogger.get_logger')
def test_process_schedules_uses_mock_taskwriter(monkeypatch, mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger

    original_init = FakeTaskWriter.__init__

    def tracking_init(self, site_id: int):
        created.append(self)
        original_init(self, site_id)

    monkeypatch.setattr(FakeTaskWriter, "__init__", tracking_init, raising=True)

    # Patch the TaskWriter used inside ScheduleDateRefresher to your mock class
    monkeypatch.setattr(ScheduleDateRefresher, "TaskWriter", FakeTaskWriter, raising=True)

    # Run
    ScheduleDateRefresher.process_schedules()

    # Assert our mock was instantiated and used
    assert len(created) == 1, "MockTaskWriter was not instantiated by process_schedules"

    # And its no-op methods should run without errors (covered by successful run)
