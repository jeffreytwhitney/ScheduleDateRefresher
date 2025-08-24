import pytest
from unittest.mock import patch, MagicMock
from TaskIDLinkRecords import TaskIDLinkRecordWriter, TaskIDLinkRecord


@patch('TaskIDLinkRecords.RefreshLogger.get_logger')
def test_add_task_id_link_record_adds_record(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    writer = TaskIDLinkRecordWriter(site_id=1)
    writer.add_task_id_link_record(101, 42, 'MachineA')
    records = writer.task_id_link_records
    assert len(records) == 1
    assert records[0].task_id == 101
    assert records[0].linked_table_name_id == 42
    assert records[0].machine_name == 'MachineA'


@patch('TaskIDLinkRecords.RefreshLogger.get_logger')
def test_task_id_link_records_property_returns_list(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    writer = TaskIDLinkRecordWriter(site_id=2)
    assert isinstance(writer.task_id_link_records, list)
    assert len(writer.task_id_link_records) == 0


@patch('TaskIDLinkRecords.DB')
@patch('TaskIDLinkRecords.RefreshLogger.get_logger')
def test_write_task_id_link_records_to_database_executes_sql(mock_get_logger, mock_db):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_db.execute_sql_statement = MagicMock()
    mock_conn = MagicMock()
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn

    writer = TaskIDLinkRecordWriter(site_id=3)
    writer.add_task_id_link_record(202, 99, 'MachineB')
    writer.write_task_id_link_records_to_database()

    mock_db.execute_sql_statement.assert_called_once_with(
        "DELETE FROM tblTaskScheduleData WHERE SiteID = 3"
    )
    assert mock_conn.execute_statement.call_count == 1
    sql = "INSERT INTO tblTaskScheduleData (TaskID, LinkedTableNameID, MachineName, SiteID) VALUES (202, 99, 'MachineB', 3)"
    mock_conn.execute_statement.assert_called_with(sql)


@patch('TaskIDLinkRecords.DB')
@patch('TaskIDLinkRecords.RefreshLogger.get_logger')
def test_write_task_id_link_records_to_database_handles_exception(mock_get_logger, mock_db):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_db.execute_sql_statement = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute_statement.side_effect = Exception("DB error")
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn

    writer = TaskIDLinkRecordWriter(site_id=4)
    writer.add_task_id_link_record(303, 100, 'MachineC')
    writer.write_task_id_link_records_to_database()

    assert mock_logger.error.called
    assert "Database error while updating TaskID Link Record" in str(mock_logger.error.call_args)
