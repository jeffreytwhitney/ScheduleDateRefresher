from typing import List

import pytest

import DB
import INIConfig
import RefreshLogger
import ScheduleDateRefresher
from Schedule import Schedule
from ScheduleInfo import ScheduleInfo
from Tasks import Task, TaskWriter
from mocks import FakeImportRecordWriter, FakeTaskIDLinkWriter, FakeTaskNameLinkWriter, make_schedule_info, FakeLogger, \
    fake_ini, get_tasks


@pytest.fixture
def schedule_info():
    site_id = 1
    schedule_id = 14

    ACTIVE_SCHEDULES_QUERY = f"SELECT * FROM tblLinkedTableNames WHERE IsActive = 1 AND SiteID = {site_id} and ID = {schedule_id}"
    records = DB.get_sql_recordset(ACTIVE_SCHEDULES_QUERY)
    record = records[0]
    config = ScheduleInfo(
        schedule_id=record['ID'],
        is_active=record['IsActive'],
        site_id=record['SiteID'],
        import_name=record['ImportName'],
        file_path=record['FilePath'],
        sheet_name=record['SheetName'],
        starting_cell_address=record['PartNumberCellName'],
        completion_date_cell_offset=record['CompletionDateOffset'],
        machine_name_offset_left=record['MachineNameOffsetLeft'],
        machine_name_offset_up=record['MachineNameOffsetUp'],
        task_name_delimiter=record['TaskNameDelimiter'],
        completion_date_delimiter=record['CompletionDateDelimeter'],
        do_part_name_trimming=record['DoPartNameTrimming']
    )

    return ScheduleInfo(
        config.schedule_id,
        config.is_active,
        config.site_id,
        config.import_name,
        config.file_path,
        config.sheet_name,
        config.starting_cell_address,
        config.completion_date_cell_offset,
        config.machine_name_offset_left,
        config.machine_name_offset_up,
        config.task_name_delimiter,
        config.completion_date_delimiter,
        config.do_part_name_trimming
    )


@pytest.mark.skip(reason="I only run this when I need to see if it processed a particular schedule and found a specific part number.")
def test_for_specific_partnumber_in_specific_schedule(monkeypatch, schedule_info):
    monkeypatch.setattr(INIConfig, "GetStoredIniValue", fake_ini, raising=True)
    monkeypatch.setattr(RefreshLogger, "get_logger", lambda *_a, **_k: FakeLogger(), raising=True)
    schedule = Schedule(schedule_info)
    import_record_writer = FakeImportRecordWriter(1)
    task_name_record_writer = FakeTaskNameLinkWriter(1)
    schedule_processor = ScheduleDateRefresher.ScheduleProcessor(1, schedule, import_record_writer, task_name_record_writer)
    schedule_processor.process_schedule()
    schedule.close()


def test_process_schedule(monkeypatch):
    monkeypatch.setattr(INIConfig, "GetStoredIniValue", fake_ini, raising=True)
    monkeypatch.setattr(RefreshLogger, "get_logger", lambda *_a, **_k: FakeLogger(), raising=True)

    schedule_info_record: ScheduleInfo = make_schedule_info(1, True, 1, "Ortho Mill Dept 1", "OrthoMill1.xlsx",
                                                            "Schedule", "D6", 23, -3, -2, "#, PART #", "COMP DATE", True)
    schedule = Schedule(schedule_info_record)
    import_record_writer = FakeImportRecordWriter(1)
    task_name_record_writer = FakeTaskNameLinkWriter(1)
    schedule_processor = ScheduleDateRefresher.ScheduleProcessor(1, schedule, import_record_writer, task_name_record_writer)
    schedule_processor.process_schedule()
    schedule.close()
    assert len(import_record_writer.import_records) == 117
    assert len(task_name_record_writer.task_name_link_records) == 139

    TaskWriter._get_tasks = get_tasks
    task_writer = TaskWriter(site_id=1)

    for import_record in import_record_writer.import_records:
        if import_record.task_name == "04.315.301":
            pass
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    task_id_link_writer = FakeTaskIDLinkWriter(1)
    for task_name_link_record in task_name_record_writer.task_name_link_records:
        tasks = task_writer.get_tasks_by_name(task_name_link_record.task_name)
        for task in tasks:
            if task_name_link_record.is_currently_running:
                task.is_currently_running = True
            task_id_link_writer.add_task_id_link_record(task.task_id, task_name_link_record.linked_table_name_id, task_name_link_record.machine_name)

    updated_tasks: List[Task] = task_writer.get_updated_tasks()
    assert len(updated_tasks) == 1
    assert updated_tasks[0].task_id == 197
    currently_running_tasks: List[Task] = task_writer.get_currently_running_tasks()
    assert len(currently_running_tasks) == 1
    assert currently_running_tasks[0].task_id == 9941
    task_id_records = task_id_link_writer.task_id_link_records
    assert len(task_id_records) == 2
    assert task_id_records[0].task_id == 9941
    assert task_id_records[0].linked_table_name_id == 1
    assert task_id_records[0].machine_name == "CELL 1 (ROBO-01A/01B)"
