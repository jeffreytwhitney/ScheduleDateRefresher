from unittest.mock import patch, MagicMock
from TaskNameLinkRecords import TaskNameLinkRecordWriter, TaskNameLinkRecord


@patch('TaskNameLinkRecords.RefreshLogger.get_logger')
def test_add_task_name_link_record_adds_records(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    writer = TaskNameLinkRecordWriter(site_id=1)
    writer.add_task_name_link_record('Task1', 42, 'MachineX', True)
    writer.add_task_name_link_record('Task2', 44, 'MachineY', False)
    records = writer.task_name_link_records
    assert len(records) == 2
    assert records[0].task_name == 'Task1'
    assert records[0].machine_name == 'MachineX'
    assert records[0].linked_table_name_id == 42
    assert records[0].is_currently_running is True
    assert records[1].task_name == 'Task2'
    assert records[1].machine_name == 'MachineY'
    assert records[1].linked_table_name_id == 44
    assert records[1].is_currently_running is False


@patch('TaskNameLinkRecords.RefreshLogger.get_logger')
def test_add_task_name_link_record_strips_quotes_and_adds_record(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    writer = TaskNameLinkRecordWriter(site_id=1)
    writer.add_task_name_link_record('Task"1\'', 42, 'Machine"X\'', True)
    records = writer.task_name_link_records
    assert len(records) == 1
    assert records[0].task_name == 'Task1'
    assert records[0].machine_name == 'MachineX'
    assert records[0].linked_table_name_id == 42
    assert records[0].is_currently_running is True


@patch('TaskNameLinkRecords.RefreshLogger.get_logger')
def test_task_name_link_records_property_returns_list(mock_get_logger):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    writer = TaskNameLinkRecordWriter(site_id=2)
    assert isinstance(writer.task_name_link_records, list)
    assert len(writer.task_name_link_records) == 0


@patch('TaskNameLinkRecords.DB')
@patch('TaskNameLinkRecords.RefreshLogger.get_logger')
def test_write_task_name_link_records_to_database_executes_sql(mock_get_logger, mock_db):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_db.execute_sql_statement = MagicMock()
    mock_conn = MagicMock()
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn

    writer = TaskNameLinkRecordWriter(site_id=3)
    writer.add_task_name_link_record('TaskA', 99, 'MachineY', False)
    writer.write_task_name_link_records_to_database()

    mock_db.execute_sql_statement.assert_called_once_with(
        "DELETE FROM tblImportMachineName WHERE SiteID = 3"
    )
    assert mock_conn.execute_statement.call_count == 1
    sql = "INSERT INTO tblImportMachineName (TaskName, LinkedTableNameID, MachineName, SiteID) VALUES ('TaskA', '99', 'MachineY', 3)"
    mock_conn.execute_statement.assert_called_with(sql)


@patch('TaskNameLinkRecords.DB')
@patch('TaskNameLinkRecords.RefreshLogger.get_logger')
def test_write_task_name_link_records_to_database_handles_exception(mock_get_logger, mock_db):
    mock_logger = MagicMock()
    mock_get_logger.return_value = mock_logger
    mock_db.execute_sql_statement = MagicMock()
    mock_conn = MagicMock()
    mock_conn.execute_statement.side_effect = Exception("DB error")
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn

    writer = TaskNameLinkRecordWriter(site_id=4)
    writer.add_task_name_link_record('TaskB', 100, 'MachineZ', True)
    writer.write_task_name_link_records_to_database()

    assert mock_logger.error.called
    assert "Database error while updating TaskID Link Record" in str(mock_logger.error.call_args)
