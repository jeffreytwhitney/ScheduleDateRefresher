from typing import List
import INIConfig
import RefreshLogger
import ScheduleDateRefresher
from Schedule import Schedule

from ScheduleInfo import ScheduleInfo
from Tasks import Task, TaskWriter
from mocks import FakeImportRecordWriter, FakeTaskIDLinkWriter
from mocks import FakeTaskNameLinkWriter
from mocks import make_schedule_info
from mocks import FakeLogger
from mocks import fake_ini
from mocks import get_tasks


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

