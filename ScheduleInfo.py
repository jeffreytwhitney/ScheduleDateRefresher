import DB
from dataclasses import dataclass
from typing import List


@dataclass
class ScheduleInfo:
    schedule_id: int
    is_active: bool
    site_id: int
    import_name: str
    file_path: str
    sheet_name: str
    starting_cell_address: str
    completion_date_cell_offset: int
    machine_name_offset_left: int
    machine_name_offset_up: int
    task_name_delimiter: str
    completion_date_delimiter: str
    do_part_name_trimming: int


def get_schedule_info_records(site_id: int) -> List[ScheduleInfo]:
    ACTIVE_SCHEDULES_QUERY = "SELECT * FROM tblLinkedTableNames WHERE IsActive = 1 AND SiteID = {site_id}"
    records = DB.get_sql_recordset(ACTIVE_SCHEDULES_QUERY.format(site_id=site_id))

    return [_create_schedule_from_record(record) for record in records]


def _create_schedule_from_record(record: dict) -> ScheduleInfo:
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
