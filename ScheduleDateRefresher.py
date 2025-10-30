import logging
import os
import shutil
import sys
import tempfile
from collections import deque

import psutil
import win32com.client

import INIConfig
import RefreshLogger
import Schedule
import ScheduleInfo
from ImportRecords import ImportRecordWriter
from ScheduleProcessor import ScheduleProcessor
from ScheduleRun import ScheduleRun
from TaskIDLinkRecords import TaskIDLinkRecordWriter
from TaskNameLinkRecords import TaskNameLinkRecordWriter
from Tasks import TaskWriter


def _get_current_directory():
    if getattr(sys, 'frozen', False):  # Check if running as an executable
        return os.path.dirname(sys.executable)
    else:  # Running as a script
        return os.path.dirname(os.path.abspath(__file__))


def _is_excel_running():
    for process in psutil.process_iter(['name']):
        if process.info['name'] and 'EXCEL' in process.info['name'].upper():
            return True
    return False


def _force_close_excel():
    try:
        # Connect to any running Excel application
        excel = win32com.client.Dispatch("Excel.Application")
        excel.Quit()  # Gracefully close Excel
    except Exception as e:
        print(f"Error while closing Excel: {e}")

    # Forcefully terminate Excel processes if still running
    os.system("taskkill /f /im excel.exe")


def _trim_log_file(log_file_name: str, max_lines: int = 10000, encoding: str = "utf-8") -> None:
    """
    Trim the file at `path` so it contains at most `max_lines` last lines.

    - Reads the file line-by-line (low memory: only keeps up to max_lines in memory).
    - If the file already has <= max_lines, it is left untouched.

    """
    if max_lines < 0:
        raise ValueError("max_lines must be non-negative")

    current_dir = _get_current_directory()
    log_file_path = current_dir + "\\" + log_file_name + ".txt"

    if not os.path.exists(log_file_path):
        return

    dq = deque(maxlen=max_lines)
    total = 0

    with open(log_file_path, "r", encoding=encoding, errors="replace") as f:
        for line in f:
            dq.append(line)
            total += 1

    kept = len(dq)

    # If nothing to trim, return early
    if total <= max_lines:
        return

    # Write to a temp file in the same directory and atomically replace
    dirpath = os.path.dirname(log_file_path) or "."
    fd, tmp_path = tempfile.mkstemp(dir=dirpath, prefix=".trimtmp-", text=True)
    try:
        # Open fd as a file object to allow specifying encoding and fsync
        with os.fdopen(fd, "w", encoding=encoding, errors="replace") as tmpf:
            tmpf.writelines(dq)
            tmpf.flush()
            os.fsync(tmpf.fileno())

        # Preserve metadata (mode, timestamps) from original
        try:
            shutil.copystat(log_file_path, tmp_path)
        except Exception:
            # If we can't copy metadata (e.g., permission), continue anyway
            pass

        # Atomic replace
        os.replace(tmp_path, log_file_path)
    except Exception:
        # Clean up tmp file on error
        try:
            os.remove(tmp_path)
        except Exception:
            pass
        raise


def process_schedules():
    """
    Processes schedules for a given site by retrieving, processing, and updating
    schedule-related data in the database. Handles errors specific to missing files or
    incorrect file headers while logging key events and statuses throughout the operation. Also
    manages task updates and ensures the synchronization of various task-related records.

    :raises Schedule.ScheduleBadHeadersError: If a schedule file has incorrect or changed headers.
    :raises Schedule.ScheduleFileNotFoundError: If a schedule file is missing or cannot be found.
    :raises Exception: For any other unexpected processing errors.
    :return: None
    """

    logger: logging.Logger = RefreshLogger.get_logger('refreshLogger')
    dblogger = RefreshLogger.get_db_logger()
    error_count: int = 0
    logger.info("Starting Run...")

    site_id = int(INIConfig.GetStoredIniValue("Site", "site", "ScheduleImporter"))
    logger.debug(f"Site ID: {site_id}")

    auto_not_scheduled = int(INIConfig.GetStoredIniValue("Switches", "auto_not_scheduled", "ScheduleImporter"))
    logger.debug(f"Auto Not Scheduled: {auto_not_scheduled}")

    schedule_run = ScheduleRun(site_id)

    runnable = schedule_run.is_runnable
    if not runnable:
        logger.info('There is nothing to run.')
        return

    logger.debug(f"Schedule Run ID: {schedule_run.schedule_run_id}")
    schedule_run.start_run()
    schedule_info_records = ScheduleInfo.get_schedule_info_records(site_id)

    import_record_writer = ImportRecordWriter(site_id)
    task_name_link_writer = TaskNameLinkRecordWriter(site_id)

    for schedule_info in schedule_info_records:
        try:
            xlschedule = Schedule.Schedule(schedule_info)
            processor = ScheduleProcessor(site_id, xlschedule, import_record_writer, task_name_link_writer)
            logger.info(f"Processing schedule {schedule_info.import_name}")
            processor.process_schedule()
            xlschedule.close()

            log_message = f"Successfully processed schedule {schedule_info.import_name}."
            logger.info(log_message)
            dblogger.info(log_message, extra={"runid":      {schedule_run.schedule_run_id},
                                              "scheduleid": {schedule_info.schedule_id}})

        except Schedule.ScheduleBadHeadersError:
            xlschedule.close()
            error_count += 1
            error_message = f"The headers (columns) for schedule {schedule_info.import_name} have change. Cannot process file."
            logger.error(error_message)
            dblogger.error(error_message, extra={"runid":      {schedule_run.schedule_run_id},
                                                 "scheduleid": {schedule_info.schedule_id}})

        except Schedule.ScheduleFileNotFoundError:
            error_count += 1
            error_message = f"Could not find file for schedule {schedule_info.import_name}."
            logger.error(error_message)
            dblogger.error(error_message, extra={"runid":      {schedule_run.schedule_run_id},
                                                 "scheduleid": {schedule_info.schedule_id}})
            xlschedule.close()

        except Exception:
            error_count += 1
            error_message = f"Processing error for schedule {schedule_info.import_name}."
            logger.error(error_message)
            dblogger.error(error_message, extra={"runid":      {schedule_run.schedule_run_id},
                                                 "scheduleid": {schedule_info.schedule_id}})
            xlschedule.close()

    task_id_link_writer = TaskIDLinkRecordWriter(site_id)
    task_writer = TaskWriter(site_id)
    for import_record in import_record_writer.import_records:
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    for task_name_link_record in task_name_link_writer.task_name_link_records:
        tasks = task_writer.get_tasks_by_name(task_name_link_record.task_name)
        for task in tasks:
            if task_name_link_record.is_currently_running:
                task.is_currently_running = True
            task_id_link_writer.add_task_id_link_record(task.task_id, task_name_link_record.linked_table_name_id, task_name_link_record.machine_name)

    import_record_count = len(import_record_writer.import_records)
    logger.info(f"Writing {import_record_count} import records to the database")

    task_link_record_count = len(task_name_link_writer.task_name_link_records)
    logger.info(f"Writing {task_link_record_count} task name link records to the database")
    task_name_link_writer.write_task_name_link_records_to_database()

    task_id_link_record_count = len(task_id_link_writer.task_id_link_records)
    logger.info(f"Writing {task_id_link_record_count} task id link records to the database")
    task_id_link_writer.write_task_id_link_records_to_database()

    task_writer_count = len(task_writer.updated_tasks)
    logger.info(f"Updating {task_writer_count} task records")
    task_writer.write_currently_running_tasks_to_database()
    task_writer.write_updated_tasks_to_database()
    task_writer.write_active_task_counts_to_database()

    if auto_not_scheduled == 1 and task_link_record_count > 0:
        logger.info(f"Setting tasks not in schedules to 'Not Scheduled'")
        task_writer.update_db_auto_not_scheduled()

    schedule_run.complete_run(error_count, task_writer_count)
    logger.info("Done processing schedules.")


if __name__ == '__main__':
    excel_is_running = _is_excel_running()
    run_local_integer = int(INIConfig.GetStoredIniValue("Switches", "run_local", "ScheduleImporter"))

    if excel_is_running:
        if run_local_integer > 0:
            input("You have Microsoft Excel already running. This can have unintended consequences. To continue, hit enter to quit this program, close Excel, and run this program again.")
            quit()
        else:
            _force_close_excel()

    process_schedules()
    _trim_log_file("ScheduleRefreshLog")

    if run_local_integer > 0:
        input("Press Enter to exit...")
