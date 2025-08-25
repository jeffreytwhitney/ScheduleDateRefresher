from unittest.mock import patch, MagicMock
from datetime import datetime

from Tasks import Task, TaskWriter


def test_task_properties():
    due = datetime(2024, 6, 1)
    sched_due = datetime(2024, 6, 2)
    task = Task(1, 2, 3, "TestTask", due, sched_due)
    assert task.task_id == 1
    assert task.projectid == 2
    assert task.statusid == 3
    assert task.taskname == "TestTask"
    assert task.duedate == due
    assert task.scheduledduedate == sched_due
    assert not task.is_currently_running
    assert not task.is_updated


def test_task_set_is_currently_running():
    task = Task(1, 2, 3, "TestTask", datetime.now(), datetime.now())
    task.is_currently_running = True
    assert task.is_currently_running


@patch('Tasks.RefreshLogger.get_logger')
@patch('Tasks.INIConfig.GetStoredIniValue')
@patch('Tasks.DB.get_sql_recordset')
def test_taskwriter_get_tasks_by_name(mock_get_sql, mock_ini, mock_logger):
    mock_ini.return_value = "auto_user"
    mock_logger.return_value = MagicMock()
    record = {
        'ID':      1, 'ProjectID': 2, 'StatusID': 3, 'TaskName': 'Alpha',
        'DueDate': '06/01/24', 'ScheduledDueDate': '06/02/24'
    }
    mock_get_sql.return_value = [record]
    writer = TaskWriter(site_id=1)
    tasks = writer.get_tasks_by_name('Alpha')
    assert len(tasks) == 1
    assert tasks[0].taskname == 'Alpha'
    assert tasks[0].duedate == datetime(2024, 6, 1)
    assert tasks[0].scheduledduedate == datetime(2024, 6, 2)


@patch('Tasks.RefreshLogger.get_logger')
@patch('Tasks.INIConfig.GetStoredIniValue')
@patch('Tasks.DB.get_sql_recordset')
def test_taskwriter_updated_and_running_tasks(mock_get_sql, mock_ini, mock_logger):
    mock_ini.return_value = "auto_user"
    mock_logger.return_value = MagicMock()
    record = {
        'ID':      1, 'ProjectID': 2, 'StatusID': 3, 'TaskName': 'Alpha',
        'DueDate': '06/01/24', 'ScheduledDueDate': '06/02/24'
    }
    mock_get_sql.return_value = [record]
    writer = TaskWriter(site_id=1)
    # Simulate updated and running
    task = writer._tasks[0]
    task._updated = True
    task._currently_running = True
    assert writer.updated_tasks == [task]
    assert writer.currently_running_tasks == [task]


@patch('Tasks.RefreshLogger.get_logger')
@patch('Tasks.INIConfig.GetStoredIniValue')
@patch('Tasks.DB.get_sql_recordset')
def test_taskwriter_update_dates_by_taskname(mock_get_sql, mock_ini, mock_logger):
    mock_ini.return_value = "auto_user"
    mock_logger.return_value = MagicMock()
    record = {
        'ID':      1, 'ProjectID': 2, 'StatusID': 3, 'TaskName': 'Alpha',
        'DueDate': '06/01/24', 'ScheduledDueDate': '06/02/24'
    }
    mock_get_sql.return_value = [record]
    writer = TaskWriter(site_id=1)
    new_due = datetime(2024, 6, 10)
    writer.update_dates_by_taskname('Alpha', new_due)
    task = writer._tasks[0]
    assert task.scheduledduedate == new_due
    assert task.is_updated


@patch('Tasks.RefreshLogger.get_logger')
@patch('Tasks.INIConfig.GetStoredIniValue')
@patch('Tasks.DB.get_sql_recordset')
@patch('Tasks.DB.DatabaseConnection')
def test_taskwriter_write_updated_tasks_to_database(mock_db_conn, mock_get_sql, mock_ini, mock_logger):
    mock_ini.return_value = "auto_user"
    mock_logger.return_value = MagicMock()
    mock_get_sql.return_value = [{
        'ID':      1, 'ProjectID': 2, 'StatusID': 3, 'TaskName': 'Alpha',
        'DueDate': '06/01/24', 'ScheduledDueDate': '06/02/24'
    }]
    mock_db = MagicMock()
    mock_db_conn.return_value.__enter__.return_value = mock_db
    writer = TaskWriter(site_id=1)
    task = writer._tasks[0]
    task._updated = True
    writer.write_updated_tasks_to_database()
    assert mock_db.execute_statement.called
