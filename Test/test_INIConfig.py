import INIConfig
import os
import shutil



def setup_module():
    test_dir = os.path.dirname(__file__)
    parent_dir = os.path.dirname(test_dir)
    parent_ini_file = f"{parent_dir}\\ScheduleImporter.ini"
    test_ini_file = f"{test_dir}\\TEST_ScheduleImporter.ini"
    if os.path.exists(test_ini_file):
        os.remove(test_ini_file)
    shutil.copyfile(parent_ini_file, test_ini_file)


def teardown_module():
    test_dir = os.path.dirname(__file__)
    test_ini_file = f"{test_dir}\\TEST_ScheduleImporter.ini"
    if os.path.exists(test_ini_file):
        os.remove(test_ini_file)


def test_site_returns_expected_value():
    value = int(INIConfig.GetStoredIniValue('Site', 'site', "//test/TEST_ScheduleImporter"))
    assert value == 1


def test_automated_user_id_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Site', 'automated_user_id', "//test/TEST_ScheduleImporter")
    assert value == "9999"
    assert isinstance(value, str)


def test_run_local_returns_expected_value():
    value = int(INIConfig.GetStoredIniValue('Switches', 'run_local', "//test/TEST_ScheduleImporter"))
    assert value == 0


def test_auto_not_scheduled_returns_expected_value():
    value = int(INIConfig.GetStoredIniValue('Switches', 'auto_not_scheduled', "//test/TEST_ScheduleImporter"))
    assert value == 0


def test_refresh_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'refreshLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_import_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'importLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_schedule_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'scheduleLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_schedule_processor_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'scheduleProcessorLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_schedule_run_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'scheduleRunLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_task_id_link_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'taskIDLinkLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_task_name_link_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'taskNameLinkLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_task_logger_returns_expected_value():
    value = INIConfig.GetStoredIniValue('Loggers', 'taskLogger', "//test/TEST_ScheduleImporter")
    assert value == "INFO"


def test_get_stored_ini_value_returns_default_for_missing_key():
    value = INIConfig.GetStoredIniValue('Site', 'NonExistentKey', "//test/TEST_ScheduleImporter")
    assert value == ''


def test_get_stored_ini_value_missing_section():
    value = INIConfig.GetStoredIniValue('NonExistentSection', 'Key', "//test/TEST_ScheduleImporter")
    assert value == ''


def test_store_ini_value_creates_section_and_key():
    INIConfig.StoreIniValue('test_value', 'TestSection', 'TestKey', "//test/TEST_ScheduleImporter")
    value = INIConfig.GetStoredIniValue('TestSection', 'TestKey', "//test/TEST_ScheduleImporter")
    assert value == 'test_value'


def test_store_ini_value_updates_existing_key():
    INIConfig.StoreIniValue('initial_value', 'UpdateSection', 'UpdateKey', "//test/TEST_ScheduleImporter")
    INIConfig.StoreIniValue('updated_value', 'UpdateSection', 'UpdateKey', "//test/TEST_ScheduleImporter")
    value = INIConfig.GetStoredIniValue('UpdateSection', 'UpdateKey', "//test/TEST_ScheduleImporter")
    assert value == 'updated_value'
