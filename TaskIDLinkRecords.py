from dataclasses import dataclass
from typing import List

import DB


@dataclass
class TaskIDLinkRecord:
    task_id: int
    linked_table_name_id: int
    machine_name: str


class TaskIDLinkRecordWriter:
    def __init__(self, site_id: int):
        self._task_id_link_records: List[TaskIDLinkRecord] = []
        self._site_id = site_id

    @property
    def task_id_link_records(self):
        return self._task_id_link_records

    def add_task_id_link_record(self, task_id: int, linked_table_name_id: int, machine_name: str):
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_id_link_records.append(TaskIDLinkRecord(task_id, linked_table_name_id, machine_name))

    def write_task_id_link_records_to_database(self):
        DB.execute_sql_statement("DELETE FROM tblTaskScheduleData WHERE SiteID = {site_id}".format(site_id=self._site_id))
        with DB.DatabaseConnection(False) as db:
            for record in self._task_id_link_records:
                sql = "INSERT INTO tblTaskScheduleData (TaskID, LinkedTableNameID, MachineName, SiteID) VALUES ({task_id}, {linked_table_name_id}, '{machine_name}', {site_id})".format(
                    task_id=record.task_id,
                    linked_table_name_id=record.linked_table_name_id,
                    machine_name=record.machine_name,
                    site_id=self._site_id
                )
                try:
                    db.execute_statement(sql)
                except:
                    print(f"Error executing SQL statement: {sql}")
