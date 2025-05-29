from dataclasses import dataclass
from typing import List

import DB
from Logger import Logger


@dataclass
class TaskNameLinkRecord:
    task_name: str
    linked_table_name_id: int
    machine_name: str


class TaskNameLinkRecordWriter:
    def __init__(self, site_id: int):
        self._task_name_link_records: List[TaskNameLinkRecord] = []
        self._site_id = site_id
        self._logger = Logger()

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
            for linkrecord in self._task_name_link_records:
                sql = f"INSERT INTO tblImportMachineName (TaskName, LinkedTableNameID, MachineName, SiteID) VALUES ('{linkrecord.task_name}', '{linkrecord.linked_table_name_id}', '{linkrecord.machine_name}', {self._site_id})"
                try:
                    db.execute_statement(sql)
                except Exception as e:
                    self._logger.log_error(f"Database error while updating TaskID Link Record. SQL statement: {sql}")
