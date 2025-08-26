import os
import csv
from typing import List

import dateutil.parser

from Tasks import TaskWriter, Task


class MockTaskWriter(TaskWriter):
    def __init__(self, site_id: int):
        super().__init__(site_id)

    def _get_tasks(self) -> List[Task]:
        current_dir = os.path.dirname(__file__)
        tasks_file = f"{current_dir}\\tasks.csv"
        tasks = []
        if os.path.exists(tasks_file):
            with open(tasks_file, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    task = Task(
                        int(row['ID']),
                        int(row['ProjectID']),
                        int(row['StatusID']),
                        row['TaskName'],
                        dateutil.parser.parse(row['DueDate']),
                        dateutil.parser.parse(row['ScheduledDueDate'])
                    )
                    tasks.append(task)
        return tasks

    def update_db_auto_not_scheduled(self):
        pass

    def write_currently_running_tasks_to_database(self):
        pass

    def write_updated_tasks_to_database(self):
        pass

