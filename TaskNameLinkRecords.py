from dataclasses import dataclass
from typing import List

import DB


@dataclass
class TaskNameLinkRecord:
    task_name: str
    linked_table_name_id: int
    machine_name: str


class TaskNameLinkRecordWriter:
    def __init__(self, site_id: int):
        self._task_name_link_records: List[TaskNameLinkRecord] = []
        self._site_id = site_id

    def add_task_name_link_record(self, task_name: str, linked_table_name_id: int, machine_name: str):
        task_name = task_name.replace("\"", "").replace("'", "")
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_name_link_records.append(TaskNameLinkRecord(task_name, linked_table_name_id, machine_name))

    @property
    def task_name_link_records(self):
        return self._task_name_link_records

    def write_task_name_link_records_to_database(self):
        DB.execute_sql_statement("DELETE FROM tblImportMachineName WHERE SiteID = {site_id}".format(site_id=self._site_id))
        with DB.DatabaseConnection(False) as db:
            for record in self._task_name_link_records:
                sql = "INSERT INTO tblImportMachineName (TaskName, LinkedTableNameID, MachineName, SiteID) VALUES ('{task_name}', '{linked_table_name_id}', '{machine_name}', {site_id})".format(
                        task_name=record.task_name,
                        linked_table_name_id=record.linked_table_name_id,
                        machine_name=record.machine_name,
                        site_id=self._site_id
                    )
                try:
                    db.execute_statement(sql)
                except:
                    pass

