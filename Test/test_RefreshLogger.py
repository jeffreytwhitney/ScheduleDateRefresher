import pytest
import logging
from unittest.mock import patch, MagicMock

import RefreshLogger


@pytest.fixture
def log_record():
    record = logging.LogRecord(
        name='test', level=logging.ERROR, pathname='', lineno=0,
        msg='Test error', args=(), exc_info=None
    )
    record.runid = [1]
    record.scheduleid = [2]
    return record


@patch('RefreshLogger.DB.execute_sql_statement')
def test_emit_error_calls_db(mock_execute, log_record):
    handler = RefreshLogger.SQLServerHandler()
    handler.emit(log_record)
    assert mock_execute.called
    sql = mock_execute.call_args[0][0]
    assert 'IsError' in sql
    assert '1' in sql


@patch('RefreshLogger.DB.execute_sql_statement')
def test_emit_non_error_calls_db(mock_execute):
    handler = RefreshLogger.SQLServerHandler()
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg='Test info', args=(), exc_info=None
    )
    record.runid = [1]
    record.scheduleid = [2]
    handler.emit(record)
    sql = mock_execute.call_args[0][0]
    assert 'IsError' in sql
    assert '0' in sql


@patch('RefreshLogger.DB.execute_sql_statement')
def test_emit_missing_ids_no_db_call(mock_execute):
    handler = RefreshLogger.SQLServerHandler()
    record = logging.LogRecord(
        name='test', level=logging.INFO, pathname='', lineno=0,
        msg='Test info', args=(), exc_info=None
    )
    record.runid = [None]
    record.scheduleid = [None]
    handler.emit(record)
    mock_execute.assert_not_called()


@patch('RefreshLogger.INIConfig.GetStoredIniValue', return_value='DEBUG')
@patch('RefreshLogger.logging.FileHandler')
@patch('RefreshLogger.logging.StreamHandler')
def test_get_logger_debug(mock_stream, mock_file, mock_ini):
    logger = RefreshLogger.get_logger('TestLogger')
    assert logger.level == logging.DEBUG
    assert mock_stream.called
    assert mock_file.called


@patch('RefreshLogger.INIConfig.GetStoredIniValue', return_value='INFO')
@patch('RefreshLogger.logging.FileHandler')
@patch('RefreshLogger.logging.StreamHandler')
def test_get_logger_info(mock_stream, mock_file, mock_ini):
    logger = RefreshLogger.get_logger('TestLogger')
    assert logger.level == logging.INFO


@patch('RefreshLogger.sys')
def test_get_current_directory_frozen(mock_sys):
    mock_sys.frozen = True
    mock_sys.executable = 'C:\\path\\to\\exe'
    result = RefreshLogger.get_current_directory()
    assert 'C:\\path\\to' in result


@patch('RefreshLogger.os.path.abspath', return_value='C:\\path\\to\\script.py')
@patch('RefreshLogger.sys')
def test_get_current_directory_script(mock_sys, mock_abspath):
    mock_sys.frozen = False
    result = RefreshLogger.get_current_directory()
    assert 'C:\\path\\to' in result


@patch('RefreshLogger.SQLServerHandler')
def test_get_db_logger(mock_sql_handler):
    logger = RefreshLogger.get_db_logger()
    assert logger.level == logging.INFO
    assert mock_sql_handler.called
