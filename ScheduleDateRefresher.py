import datetime

import DB
import INIConfig
import Schedule
import ScheduleInfo
from ImportRecords import ImportRecordWriter
from ScheduleProcessor import ScheduleProcessor
from ScheduleRun import ScheduleRun
from TaskIDLinkRecords import TaskIDLinkRecordWriter
from TaskNameLinkRecords import TaskNameLinkRecordWriter
from Tasks import TaskWriter


def process_schedules():
    error_count: int = 0
    formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print("Starting:", formatted_datetime)

    site_id = int(INIConfig.GetStoredIniValue("Site", "site", "ScheduleImporter"))
    schedule_run = ScheduleRun(site_id)
    runnable = schedule_run.is_runnable
    if not runnable:
        print('Dont run yet')
        return
    schedule_run.start_run()
    schedule_info_records = ScheduleInfo.get_schedule_info_records(site_id)

    import_record_writer = ImportRecordWriter(site_id)
    task_name_link_writer = TaskNameLinkRecordWriter(site_id)

    for schedule_info in schedule_info_records:
        try:

            xlschedule = Schedule.Schedule(schedule_info)
            processor = ScheduleProcessor(site_id, schedule_run, xlschedule, import_record_writer, task_name_link_writer)
            formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            print(f"Processing schedule {schedule_info.import_name} at {formatted_datetime}")
            processor.process_schedule()
            xlschedule.close()
            log_message = f"Successfully processed schedule {schedule_info.import_name}."
            _write_log_to_db(schedule_run.schedule_run_id, schedule_info.schedule_id, log_message)
        except Schedule.ScheduleBadHeadersError:
            error_count += 1
            error_message = f"The headers (columns) for schedule {schedule_info.import_name} have change. Cannot process file."
            _write_error_to_db(schedule_run.schedule_run_id, schedule_info.schedule_id, error_message)
        except Schedule.ScheduleFileNotFoundError:
            error_count += 1
            error_message = f"Could not find file for schedule {schedule_info.schedule_id}."
            _write_error_to_db(schedule_run.schedule_run_id, schedule_info.schedule_id, error_message)

    task_id_link_writer = TaskIDLinkRecordWriter(site_id)
    task_writer = TaskWriter(site_id)
    for import_record in import_record_writer.import_records:
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    for task_name_link_record in task_name_link_writer.task_name_link_records:
        tasks = task_writer.get_tasks_by_name(task_name_link_record.task_name)
        for task in tasks:
            task_id_link_writer.add_task_id_link_record(task.task_id, task_name_link_record.linked_table_name_id, task_name_link_record.machine_name)

    import_record_count = len(import_record_writer.import_records)
    print(f"Writing {import_record_count} import records to the database")
    import_record_writer.write_import_records_to_database()

    task_link_record_count = len(task_name_link_writer.task_name_link_records)
    print(f"Writing {task_link_record_count} task name link records to the database")
    task_name_link_writer.write_task_name_link_records_to_database()

    task_id_link_record_count = len(task_id_link_writer.task_id_link_records)
    print(f"Writing {task_id_link_record_count} task id link records to the database")
    task_id_link_writer.write_task_id_link_records_to_database()

    task_writer_count = len(task_writer.updated_tasks)
    print(f"Updating {task_writer_count} task records")
    task_writer.write_updated_tasks_to_database()

    formatted_datetime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    schedule_run.complete_run(error_count)
    print(f"Done at {formatted_datetime}")


def _write_error_to_db(runid, schedule_id, error_message: str):
    sql: str = f"Insert into tblScheduleRunLog (ScheduleRunEntryID, ScheduleID, LogMessage, IsError) values ({runid}, {schedule_id}, '{error_message}', 1)"
    DB.execute_sql_statement(sql)


def _write_log_to_db(runid, schedule_id, log_message: str):
    sql: str = f"Insert into tblScheduleRunLog (ScheduleRunEntryID, ScheduleID, LogMessage, IsError) values ({runid}, {schedule_id}, '{log_message}', 0)"
    DB.execute_sql_statement(sql)


if __name__ == '__main__':
    process_schedules()
