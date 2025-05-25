from dataclasses import dataclass
from datetime import datetime
from typing import List

import DB


@dataclass
class ImportRecord:
    task_name: str
    due_date: datetime


class ImportRecordWriter:
    def __init__(self, site_id: int):
        self._records: List[ImportRecord] = []
        self._site_id = site_id

    def add_import_record(self, task_name: str, due_date: datetime):
        existing_records = [record for record in self._records if record.task_name == task_name]
        if not existing_records:
            self._records.append(ImportRecord(task_name, due_date))
        else:
            existing_due_date = existing_records[0].due_date
            if due_date < existing_due_date:
                existing_records[0].due_date = due_date

    @property
    def import_records(self) -> List[ImportRecord]:
        return self._records

    def write_import_records_to_database(self):
        DB.execute_sql_statement("DELETE FROM tblImport WHERE SiteID = {site_id}".format(site_id=self._site_id))

        for record in self._records:
            DB.execute_sql_statement(
                "INSERT INTO tblImport (TaskName, DueDate, SiteID) VALUES ('{task_name}', '{due_date}', {site_id})".format(
                    task_name=record.task_name,
                    due_date=record.due_date,
                    site_id=self._site_id
                )
            )
