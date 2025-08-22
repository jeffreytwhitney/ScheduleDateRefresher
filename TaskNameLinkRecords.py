import logging.config
from dataclasses import dataclass
from typing import List
import Lib
import DB


@dataclass
class TaskNameLinkRecord:
    task_name: str
    linked_table_name_id: int
    machine_name: str
    is_currently_running: bool


class TaskNameLinkRecordWriter:
    _logger: logging.Logger

    def __init__(self, site_id: int):
        self._task_name_link_records: List[TaskNameLinkRecord] = []
        self._site_id = site_id
        conf_path = Lib.get_current_directory() + "\\logging.conf"
        logging.config.fileConfig(conf_path)
        self._logger = logging.getLogger('taskNameLinkLogger')

    def add_task_name_link_record(self, task_name: str, linked_table_name_id: int, machine_name: str, currently_running: bool):
        self._logger.debug(f"Adding task name link record for task name '{task_name}' with linked table name ID '{linked_table_name_id}' and machine name '{machine_name}'")
        task_name = task_name.replace("\"", "").replace("'", "")
        machine_name = machine_name.replace("\"", "").replace("'", "")
        self._task_name_link_records.append(TaskNameLinkRecord(task_name, linked_table_name_id, machine_name, currently_running))

    @property
    def task_name_link_records(self):
        return self._task_name_link_records

    def write_task_name_link_records_to_database(self):
        self._logger.debug("Writing task name link records to database.")
        DB.execute_sql_statement("DELETE FROM tblImportMachineName WHERE SiteID = {site_id}".format(site_id=self._site_id))
        with DB.DatabaseConnection(False) as db:
            for linkrecord in self._task_name_link_records:
                self._logger.debug(f"Writing task name link record for task name '{linkrecord.task_name}' with linked table name ID '{linkrecord.linked_table_name_id}' and machine name '{linkrecord.machine_name}'")
                sql = f"INSERT INTO tblImportMachineName (TaskName, LinkedTableNameID, MachineName, SiteID) VALUES ('{linkrecord.task_name}', '{linkrecord.linked_table_name_id}', '{linkrecord.machine_name}', {self._site_id})"
                try:
                    db.execute_statement(sql)
                except Exception as e:
                    self._logger.error(f"Database error while updating TaskID Link Record. SQL statement: {sql}")
