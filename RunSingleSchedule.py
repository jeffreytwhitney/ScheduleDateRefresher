"""Process a single schedule for debugging.

Set the constants below (SCHEDULE, WRITE_TO_DB, LIST_SCHEDULES) and press Run/Debug in PyCharm.

A dry run reads and processes the schedule and prints what would be written, but touches
nothing in the database. Exceptions are not swallowed, so the debugger stops where they occur.
"""
import Config
import ScheduleInfo
from ImportRecords import ImportRecordWriter
from Schedule import Schedule
from ScheduleProcessor import ScheduleProcessor
from TaskIDLinkRecords import TaskIDLinkRecordWriter
from TaskNameLinkRecords import TaskNameLinkRecordWriter
from Tasks import TaskWriter

# Edit these, then press Run/Debug in PyCharm.
SCHEDULE = "Additive Mill 1"  # ImportName or ID
WRITE_TO_DB = False
LIST_SCHEDULES = False  # List active schedules and exit


def find_schedule(records, key: str):
    key = key.strip().upper()
    matches = [r for r in records if r.import_name.upper() == key or str(r.schedule_id) == key]
    if not matches:
        matches = [r for r in records if key in r.import_name.upper()]
    if len(matches) != 1:
        names = ", ".join(r.import_name for r in matches) or "none"
        raise SystemExit(f"Expected exactly one schedule matching '{key}', found: {names}")
    return matches[0]


def run(schedule_key: str, write: bool) -> None:
    site_id = int(Config.get_env_value("SITE", "0"))
    records = ScheduleInfo.get_schedule_info_records(site_id)
    schedule_info = find_schedule(records, schedule_key)
    print(f"Schedule: {schedule_info.import_name} (ID {schedule_info.schedule_id}, "
          f"remote={schedule_info.is_remote}) path={schedule_info.file_path}")

    import_record_writer = ImportRecordWriter(site_id)
    task_name_link_writer = TaskNameLinkRecordWriter(site_id)

    xlschedule = Schedule(schedule_info)
    try:
        processor = ScheduleProcessor(site_id, xlschedule, import_record_writer, task_name_link_writer)
        processor.process_schedule()  # set a breakpoint here or step into it
    finally:
        xlschedule.close()

    print(f"Import records: {len(import_record_writer.import_records)}")
    for record in import_record_writer.import_records:
        print(f"  {record.task_name}  due {record.due_date}")
    print(f"Task name link records: {len(task_name_link_writer.task_name_link_records)}")

    if not write:
        print("Dry run: nothing written to the database. Set WRITE_TO_DB = True to save.")
        return

    task_id_link_writer = TaskIDLinkRecordWriter(site_id)
    task_writer = TaskWriter(site_id)
    for import_record in import_record_writer.import_records:
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    for link in task_name_link_writer.task_name_link_records:
        for task in task_writer.get_tasks_by_name(link.task_name):
            if link.is_currently_running:
                task.is_currently_running = True
            task_id_link_writer.add_task_id_link_record(task.task_id, link.linked_table_name_id, link.machine_name)

    task_name_link_writer.write_task_name_link_records_to_database()
    task_id_link_writer.write_task_id_link_records_to_database()
    task_writer.write_currently_running_tasks_to_database()
    task_writer.write_updated_tasks_to_database()
    task_writer.write_active_task_counts_to_database()
    print(f"Wrote {len(task_writer.updated_tasks)} updated tasks.")


def main() -> None:
    if LIST_SCHEDULES or not SCHEDULE:
        site_id = int(Config.get_env_value("SITE", "1"))
        for r in ScheduleInfo.get_schedule_info_records(site_id):
            print(f"{r.schedule_id:>5}  {r.import_name}  {'[remote]' if r.is_remote else ''}")
        return

    run(SCHEDULE, WRITE_TO_DB)


if __name__ == "__main__":
    main()
