import os

import xlwings

import DB
import RefreshLogger
import RemoteFile
from Schedule import matches_completion_date_delimiter, matches_task_name_delimiter, task_name_delimiters
from ScheduleInfo import ScheduleInfo


_INSERT_CHANGE = """
DECLARE @now datetime = GETDATE();
DECLARE @today date = CONVERT(date, @now);

INSERT INTO dbo.tblScheduleChangeLog
    (ScheduleID, EmailSent, ChangeMessage, CreateTimestamp, EmailSentTimestamp)
SELECT %s, 0, %s, @now, NULL
WHERE NOT EXISTS (
    SELECT 1
    FROM dbo.tblScheduleChangeLog WITH (UPDLOCK, HOLDLOCK)
    WHERE ScheduleID = %s
      AND (EmailSent = 0 OR (CreateTimestamp >= @today AND CreateTimestamp < DATEADD(day, 1, @today)))
);
"""


def check_schedule(schedule_info: ScheduleInfo) -> None:
    """Check a schedule and queue one change-log entry if notification is due."""
    problems = _find_problems(schedule_info)
    if problems:
        message = "; ".join(problems)
        RefreshLogger.get_logger("scheduleLogger").warning(
            "Schedule %s: %s", schedule_info.import_name, message)
        DB.execute_sql_statement(
            _INSERT_CHANGE, (schedule_info.schedule_id, message[:1000], schedule_info.schedule_id))


def _find_problems(schedule_info: ScheduleInfo) -> list[str]:
    filepath = schedule_info.file_path
    local_copy = None
    try:
        if schedule_info.is_remote:
            try:
                local_copy = RemoteFile.download_to_working_dir(filepath)
            except FileNotFoundError:
                return ["Could not find or download the remote schedule file."]
            filepath = local_copy

        if not os.path.isfile(filepath):
            return ["Schedule file not found."]

        with xlwings.App(visible=False, add_book=False) as app:
            app.display_alerts = False
            app.api.AutomationSecurity = 3  # msoAutomationSecurityForceDisable
            book = app.books.open(filepath, update_links=False, read_only=True)
            try:
                return _check_headers(book, schedule_info)
            finally:
                book.close()
    finally:
        if local_copy is not None:
            RemoteFile.delete_local_file(local_copy)


def _check_headers(book: xlwings.Book, schedule_info: ScheduleInfo) -> list[str]:
    if not any(sheet.name.lower() == schedule_info.sheet_name.lower() for sheet in book.sheets):
        return [f"Worksheet {schedule_info.sheet_name!r} not found."]

    sheet = book.sheets[schedule_info.sheet_name]
    task_cell = sheet.range(schedule_info.starting_cell_address)
    date_cell = task_cell.offset(0, schedule_info.completion_date_cell_offset)
    task_value = task_cell.value
    date_value = date_cell.value

    problems = []
    if not matches_task_name_delimiter(task_value, task_name_delimiters(schedule_info.task_name_delimiter)):
        problems.append(_header_mismatch("Task name", task_cell, schedule_info.task_name_delimiter, task_value))
    if not matches_completion_date_delimiter(date_value, schedule_info.completion_date_delimiter):
        problems.append(_header_mismatch("Completion date", date_cell, schedule_info.completion_date_delimiter,
                                         date_value))
    return problems


def _header_mismatch(label: str, cell: xlwings.Range, expected: str, actual: object) -> str:
    address = cell.get_address(row_absolute=False, column_absolute=False, include_sheetname=True)
    return f"{label} header at {address}: expected {expected!r}, found {repr(actual)[:200]}"
