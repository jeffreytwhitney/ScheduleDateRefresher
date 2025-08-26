from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

import ImportRecords


@pytest.fixture
def writer():
    with patch('ImportRecords.RefreshLogger.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        return ImportRecords.ImportRecordWriter(site_id=1)


def test_add_import_record_adds_new(writer):
    writer.add_import_record('Task1', datetime(2024, 6, 1))
    assert len(writer.import_records) == 1
    assert writer.import_records[0].task_name == 'Task1'


def test_add_import_record_strips_quotes(writer):
    writer.add_import_record('"Task2\'"', datetime(2024, 6, 2))
    assert writer.import_records[0].task_name == 'Task2'


def test_add_import_record_updates_due_date(writer):
    due1 = datetime(2024, 6, 3)
    due2 = due1 - timedelta(days=1)
    writer.add_import_record('Task3', due1)
    writer.add_import_record('Task3', due2)
    assert len(writer.import_records) == 1
    assert writer.import_records[0].due_date == due2


def test_add_import_record_does_not_update_due_date_if_later(writer):
    due1 = datetime(2024, 6, 3)
    due2 = due1 + timedelta(days=1)
    writer.add_import_record('Task4', due1)
    writer.add_import_record('Task4', due2)
    assert writer.import_records[0].due_date == due1


@patch('ImportRecords.DB')
def test_write_import_records_to_database_calls_db(mock_db, writer):
    writer.add_import_record('Task5', datetime(2024, 6, 5))
    mock_conn = MagicMock()
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn
    writer.write_import_records_to_database()
    mock_db.execute_sql_statement.assert_called_once_with("DELETE FROM tblImport WHERE SiteID = 1")
    assert mock_conn.execute_statement.call_count == 1
    sql = mock_conn.execute_statement.call_args[0][0]
    assert "INSERT INTO tblImport" in sql
    assert "Task5" in sql


@patch('ImportRecords.DB')
def test_write_import_records_to_database_handles_exception(mock_db, writer):
    writer.add_import_record('Task6', datetime(2024, 6, 6))
    mock_conn = MagicMock()
    mock_conn.execute_statement.side_effect = Exception("DB error")
    mock_db.DatabaseConnection.return_value.__enter__.return_value = mock_conn
    writer.write_import_records_to_database()
    # Should log an error, but not raise
    assert mock_conn.execute_statement.called
    assert writer._logger.error.called
