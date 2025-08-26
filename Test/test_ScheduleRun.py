from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from ScheduleRun import ScheduleRun, ScheduleRunConfig


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.INIConfig.GetStoredIniValue')
@patch('ScheduleRun.DB.get_sql_scalar')
@patch('ScheduleRun.DB.get_sql_recordset')
@patch('ScheduleRun.os.getlogin')
def test_init_runnable_local_run(
    mock_getlogin, mock_get_sql_recordset, mock_get_sql_scalar, mock_ini, mock_logger
):
    # Setup mocks
    mock_logger.return_value = MagicMock()
    mock_ini.return_value = 1  # run_local enabled
    mock_getlogin.return_value = 'testuser'
    mock_get_sql_scalar.side_effect = [123, 1]  # user_id, runnable count
    mock_get_sql_recordset.return_value = [{
        'ID':                        10,
        'RunDateTime':               datetime(2024, 6, 1, 8, 0),
        'StartTimestamp':            datetime(2024, 6, 1, 8, 5),
        'CompletionTimestamp':       datetime(2024, 6, 1, 9, 0),
        'RequestUserEmployeeNumber': '123',
        'RequesterName':             'Test User',
        'IsAutomated':               0,
        'IsComplete':                0
    }]
    with patch.object(ScheduleRun, '_create_local_run_entry') as mock_local_entry:
        run = ScheduleRun(site_id=1)
        assert run.is_runnable
        assert run._run_local
        assert run._run_local_employee_number == '123'
        assert run.schedule_run_id == 10
        assert run.request_user_name == 'Test User'
        mock_local_entry.assert_called_once()


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.INIConfig.GetStoredIniValue')
@patch('ScheduleRun.DB.get_sql_scalar')
@patch('ScheduleRun.DB.get_sql_recordset')
def test_init_not_runnable(
    mock_get_sql_recordset, mock_get_sql_scalar, mock_ini, mock_logger
):
    mock_logger.return_value = MagicMock()
    mock_ini.return_value = 0  # run_local disabled
    mock_get_sql_scalar.return_value = 0  # not runnable
    run = ScheduleRun(site_id=2)
    assert not run.is_runnable


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.DB.execute_sql_statement')
def test_start_run_and_complete_run(mock_exec_sql, mock_logger):
    mock_logger.return_value = MagicMock()
    run = ScheduleRun.__new__(ScheduleRun)
    run._logger = mock_logger.return_value
    run._schedule_run_config = MagicMock(schedule_run_id=5)
    run._run_local = False
    with patch.object(run, '_create_automated_run_entry') as mock_auto_entry:
        run.start_run()
        assert mock_exec_sql.called
        run.complete_run(error_count=2, updated_task_count=3)
        assert mock_exec_sql.call_count == 2
        mock_auto_entry.assert_called_once()


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.DB.get_sql_recordset')
def test_get_schedule_run_config(mock_get_sql_recordset, mock_logger):
    mock_logger.return_value = MagicMock()
    run = ScheduleRun.__new__(ScheduleRun)
    run._logger = mock_logger.return_value
    run._site_id = 1
    record = {
        'ID':                        20,
        'RunDateTime':               datetime(2024, 6, 2, 10, 0),
        'StartTimestamp':            datetime(2024, 6, 2, 10, 5),
        'CompletionTimestamp':       datetime(2024, 6, 2, 11, 0),
        'RequestUserEmployeeNumber': '456',
        'RequesterName':             'Another User',
        'IsAutomated':               1,
        'IsComplete':                1
    }
    mock_get_sql_recordset.return_value = [record]
    config = run._get_schedule_run_config()
    assert isinstance(config, ScheduleRunConfig)
    assert config.schedule_run_id == 20
    assert config.request_user_name == 'Another User'


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.DB.get_sql_recordset')
def test_generate_new_run_datetime_next_run_today(mock_get_sql_recordset, mock_logger):
    mock_logger.return_value = MagicMock()
    run = ScheduleRun.__new__(ScheduleRun)
    run._logger = mock_logger.return_value
    run._site_id = 1
    now = datetime.now()
    later_time = (now + timedelta(minutes=10)).time()
    mock_get_sql_recordset.return_value = [{'RunTime': later_time}]
    result = run._generate_new_run_datetime()
    assert result.startswith(now.strftime('%Y-%m-%d'))


@patch('ScheduleRun.RefreshLogger.get_logger')
@patch('ScheduleRun.DB.get_sql_recordset')
def test_generate_new_run_datetime_next_run_tomorrow(mock_get_sql_recordset, mock_logger):
    mock_logger.return_value = MagicMock()
    run = ScheduleRun.__new__(ScheduleRun)
    run._logger = mock_logger.return_value
    run._site_id = 1
    now = datetime.now()
    earlier_time = (now - timedelta(minutes=10)).time()
    mock_get_sql_recordset.return_value = [{'RunTime': earlier_time}]
    result = run._generate_new_run_datetime()
    tomorrow = (now + timedelta(days=1)).strftime('%Y-%m-%d')
    assert result.startswith(tomorrow)
