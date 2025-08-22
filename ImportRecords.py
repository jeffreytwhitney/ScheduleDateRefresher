from dataclasses import dataclass
from datetime import datetime
from typing import List
import logging.config
import logging
import DB
import Lib

@dataclass
class ImportRecord:
    task_name: str
    due_date: datetime


class ImportRecordWriter:
    _logger: logging.Logger
    _records: List[ImportRecord]
    _site_id: int = 0
    _logger: logging.Logger

    def __init__(self, site_id: int):
        self._records: List[ImportRecord] = []
        self._site_id = site_id
        conf_path = Lib.get_current_directory() + "\\logging.conf"
        logging.config.fileConfig(conf_path)
        self._logger = logging.getLogger('importLogger')

    def add_import_record(self, task_name: str, due_date: datetime):
        self._logger.debug(f"Adding import record for task '{task_name}' with due date '{due_date}'")
        task_name = task_name.replace("\"", "").replace("'", "")

        existing_records = [record for record in self._records if record.task_name == task_name]
        if not existing_records:
            self._logger.debug(f"No existing record found for task '{task_name}'. Adding new record.")
            self._records.append(ImportRecord(task_name, due_date))
        else:
            self._logger.debug(f"Existing record found for task '{task_name}'. Updating due date.")
            existing_due_date = existing_records[0].due_date
            if due_date < existing_due_date:
                existing_records[0].due_date = due_date

    @property
    def import_records(self) -> List[ImportRecord]:
        return self._records

    def write_import_records_to_database(self):
        self._logger.debug("Writing import records to database.")
        DB.execute_sql_statement("DELETE FROM tblImport WHERE SiteID = {site_id}".format(site_id=self._site_id))
        with (DB.DatabaseConnection(False) as db):
            for record in self._records:
                self._logger.debug(f"Writing import record for task '{record.task_name}' with due date '{record.due_date}'")
                formatted_task_name = record.task_name.replace("\"", "").replace("'", "")
                sql = f"INSERT INTO tblImport (TaskName, DueDate, SiteID) VALUES ('{formatted_task_name}', '{record.due_date}', {self._site_id})"
                try:
                    db.execute_statement(sql)
                except Exception as e:
                    self._logger.error(f"Database error while updating Import Record. SQL statement: {sql}")
