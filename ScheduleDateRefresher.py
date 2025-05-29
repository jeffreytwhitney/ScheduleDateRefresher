import INIConfig
import Schedule
import ScheduleInfo
from ImportRecords import ImportRecordWriter
from Logger import Logger
from ScheduleProcessor import ScheduleProcessor
from ScheduleRun import ScheduleRun
from TaskIDLinkRecords import TaskIDLinkRecordWriter
from TaskNameLinkRecords import TaskNameLinkRecordWriter
from Tasks import TaskWriter


def process_schedules():
    logger = Logger()
    error_count: int = 0
    logger.log_message(f"Starting run")

    site_id = int(INIConfig.GetStoredIniValue("Site", "site", "ScheduleImporter"))
    schedule_run = ScheduleRun(site_id)
    runnable = schedule_run.is_runnable
    if not runnable:
        logger.log_message('There is nothing to run.')
        return
    schedule_run.start_run()
    schedule_info_records = ScheduleInfo.get_schedule_info_records(site_id)

    import_record_writer = ImportRecordWriter(site_id)
    task_name_link_writer = TaskNameLinkRecordWriter(site_id)

    for schedule_info in schedule_info_records:
        try:
            xlschedule = Schedule.Schedule(schedule_info)
            processor = ScheduleProcessor(site_id, schedule_run, xlschedule, import_record_writer, task_name_link_writer)
            logger.log_message(f"Processing schedule {schedule_info.import_name}")
            processor.process_schedule()
            xlschedule.close()
            log_message = f"Successfully processed schedule {schedule_info.import_name}."
            logger.log_schedule_run_message(schedule_run.schedule_run_id, schedule_info.schedule_id, log_message)
        except Schedule.ScheduleBadHeadersError:
            error_count += 1
            error_message = f"The headers (columns) for schedule {schedule_info.import_name} have change. Cannot process file."
            logger.log_schedule_run_error(schedule_run.schedule_run_id, schedule_info.schedule_id, error_message)
        except Schedule.ScheduleFileNotFoundError:
            error_count += 1
            error_message = f"Could not find file for schedule {schedule_info.schedule_id}."
            logger.log_schedule_run_error(schedule_run.schedule_run_id, schedule_info.schedule_id, error_message)

    task_id_link_writer = TaskIDLinkRecordWriter(site_id)
    task_writer = TaskWriter(site_id)
    for import_record in import_record_writer.import_records:
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    for task_name_link_record in task_name_link_writer.task_name_link_records:
        tasks = task_writer.get_tasks_by_name(task_name_link_record.task_name)
        for task in tasks:
            task_id_link_writer.add_task_id_link_record(task.task_id, task_name_link_record.linked_table_name_id, task_name_link_record.machine_name)

    import_record_count = len(import_record_writer.import_records)
    logger.log_message(f"Writing {import_record_count} import records to the database")
    import_record_writer.write_import_records_to_database()

    task_link_record_count = len(task_name_link_writer.task_name_link_records)
    logger.log_message(f"Writing {task_link_record_count} task name link records to the database")
    task_name_link_writer.write_task_name_link_records_to_database()

    task_id_link_record_count = len(task_id_link_writer.task_id_link_records)
    logger.log_message(f"Writing {task_id_link_record_count} task id link records to the database")
    task_id_link_writer.write_task_id_link_records_to_database()

    task_writer_count = len(task_writer.updated_tasks)
    logger.log_message(f"Updating {task_writer_count} task records")
    task_writer.write_updated_tasks_to_database()

    schedule_run.complete_run(error_count)
    logger.log_message("Done processing schedules.")


if __name__ == '__main__':
    process_schedules()
