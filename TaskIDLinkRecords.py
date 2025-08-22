from dataclasses import dataclass
from logging import Logger
from typing import List
import logging.config
import Lib
import DB



@dataclass
class TaskIDLinkRecord:
    task_id: int
    linked_table_name_id: int
    machine_name: str


class TaskIDLinkRecordWriter:
    _logger: logging.Logger
    def __init__(self, site_id: int):
        self._task_id_link_records: List[TaskIDLinkRecord] = []
        self._site_id = site_id
        conf_path = Lib.get_current_directory() + "\\logging.conf"
        logging.config.fileConfig(conf_path)
        self._logger = logging.getLogger('taskIDLinkLogger')

    @property
    def task_id_link_records(self):
        return self._task_id_link_records

    def add_task_id_link_record(self, task_id: int, linked_table_name_id: int, machine_name: str):
        self._logger.debug(f"Adding task ID link record for task ID '{task_id}' with linked table name ID '{linked_table_name_id}' and machine name '{machine_name}'")
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_id_link_records.append(TaskIDLinkRecord(task_id, linked_table_name_id, machine_name))

    def write_task_id_link_records_to_database(self):
        self._logger.debug("Writing task ID link records to database.")
        DB.execute_sql_statement("DELETE FROM tblTaskScheduleData WHERE SiteID = {site_id}".format(site_id=self._site_id))
        with DB.DatabaseConnection(False) as db:
            for record in self._task_id_link_records:
                self._logger.debug(f"Writing task ID link record for task ID '{record.task_id}' with linked table name ID '{record.linked_table_name_id}' and machine name '{record.machine_name}'")
                sql = f"INSERT INTO tblTaskScheduleData (TaskID, LinkedTableNameID, MachineName, SiteID) VALUES ({record.task_id}, {record.linked_table_name_id}, '{record.machine_name}', {self._site_id})"
                try:
                    db.execute_statement(sql)
                except Exception as e:
                    self._logger.error(f"Database error while updating TaskID Link Record. SQL statement: {sql}")
