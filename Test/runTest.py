from datetime import datetime, timedelta

import DB
import INIConfig
import ScheduleInfo
from ImportRecords import ImportRecordWriter
from Schedule import Schedule
from ScheduleProcessor import ScheduleProcessor
from ScheduleRun import ScheduleRun
from TaskIDLinkRecords import TaskIDLinkRecordWriter
from TaskNameLinkRecords import TaskNameLinkRecordWriter
from Tasks import TaskWriter


def run_just_schedule_run():

    create_datetime = datetime.now() - timedelta(minutes=1)
    sql: str = f"Insert into dbo.tblScheduleRunEntry (SiteID, RunDateTime, RequestUserEmployeeNumber, IsAutomated) values (1, '{create_datetime.strftime('%Y-%m-%d %H:%M:%S')}', '4404', 0)"
    DB.execute_sql_statement(sql)

    schedule_run = ScheduleRun(1)
    schedule_run.start_run()
    schedule_run.complete_run()


def run_test():
    site_id = int(INIConfig.GetStoredIniValue("Site", "site", "ScheduleImporter"))
    schedule_run = ScheduleRun(site_id)
    test_run_id = schedule_run.schedule_run_id
    schedule_run.start_run()
    schedule_info_records = ScheduleInfo.get_schedule_info_records(site_id)
    import_record_writer = ImportRecordWriter(site_id)
    task_name_link_writer = TaskNameLinkRecordWriter(site_id)

    schedule_info = [info for info in schedule_info_records if info.import_name == 'Pacing Wires']
    xlschedule = Schedule(schedule_info[0])
    processor = ScheduleProcessor(site_id, schedule_run, xlschedule, import_record_writer, task_name_link_writer)
    processor.process_schedule()

    task_id_link_writer = TaskIDLinkRecordWriter(site_id)
    task_writer = TaskWriter(site_id)
    for import_record in import_record_writer.import_records:
        task_writer.update_dates_by_taskname(import_record.task_name, import_record.due_date)

    for task_name_link_record in task_name_link_writer.task_name_link_records:
        tasks = task_writer.get_tasks_by_name(task_name_link_record.task_name)
        for task in tasks:
            task_id_link_writer.add_task_id_link_record(task.task_id, task_name_link_record.linked_table_name_id, task_name_link_record.machine_name)

    task_id_link_writer.write_task_id_link_records_to_database()
    DB.execute_sql_statement(f"Delete from dbo.tblScheduleRunLog where ScheduleRunEntryID = {test_run_id}")

    xlschedule.close()


if __name__ == '__main__':
    #run_test()
    run_just_schedule_run()
