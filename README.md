# Schedule Date Refresher

Schedule Date Refresher reads active Excel schedules configured for a site, matches schedule entries to tasks in SQL Server, and updates task due dates and schedule/task links. It also records schedule-run status and logs processing results.

## Requirements

- Windows
- Python 3.10 or later
- Microsoft Excel desktop (the schedules are read through `xlwings`)
- Access to the SQL Server database and the tables, views, and stored procedures used by the application
- Python packages: `msal`, `psutil`, `pymssql`, `python-dateutil`, `python-dotenv`, `pywin32`, `requests`, and `xlwings`

## Setup

1. Clone the repository and create/activate a Python virtual environment.
2. Install the packages listed above. To run the tests, also install `pytest`.
3. Copy `.env_example` to `.env` in the repository root, then replace the database and Microsoft Entra placeholders with your values. The file includes the available application settings:

   ```dotenv
   DB_SERVER=your-sql-server
   DB_NAME=your-database-name
   DB_USER=your-database-user
   DB_PASSWORD=your-database-password
   CLIENT_ID=your-microsoft-application-client-id
   AUTHORITY=https://login.microsoftonline.com/organizations
   SCOPES=Files.Read
   SITE=1
   AUTOMATED_USER_ID=9999
   AUTO_NOT_SCHEDULED=0
   LOG_LEVEL_REFRESHLOGGER=INFO
   LOG_LEVEL_IMPORTLOGGER=INFO
   LOG_LEVEL_SCHEDULELOGGER=INFO
   LOG_LEVEL_SCHEDULEPROCESSORLOGGER=INFO
   LOG_LEVEL_SCHEDULERUNLOGGER=INFO
   LOG_LEVEL_TASKIDLINKLOGGER=INFO
   LOG_LEVEL_TASKNAMELINKLOGGER=INFO
   LOG_LEVEL_TASKLOGGER=INFO
   RUN_LOCAL=1
   ```

   For remote schedules, configure the Microsoft Entra public-client application ID and authority for your organization. `SCOPES` is a space- or comma-separated list of Microsoft Graph delegated permissions. Sign-in uses the device-code flow. Keep credentials private; do not commit `.env`.
4. Set the target site and run behavior in `.env`. The active schedules, Excel file paths, sheet names, and cell layouts are read from SQL Server.
5. Ensure the configured Excel files are accessible to the Windows account running the program.

## Configuration

Settings are read from environment variables, loaded from `.env` in the application directory.

| Variable | Purpose |
| --- | --- |
| `DB_SERVER` | SQL Server host or instance name |
| `DB_NAME` | Database name |
| `DB_USER` | SQL Server login |
| `DB_PASSWORD` | SQL Server login password |
| `CLIENT_ID` | Microsoft Entra public-client application ID, required for remote schedules |
| `AUTHORITY` | Microsoft identity authority used for sign-in |
| `SCOPES` | Microsoft Graph delegated permissions; separate multiple scopes with spaces or commas |
| `SITE` | SQL Server site ID to process |
| `AUTOMATED_USER_ID` | Employee number used for automated task updates |
| `AUTO_NOT_SCHEDULED` | `1` enables marking tasks not represented in schedules as "Not Scheduled" when task link records were found |
| `RUN_LOCAL` | `1` creates a local run entry and waits for confirmation before exit; `0` processes the scheduled run and closes Excel if Excel is already running |
| `LOG_LEVEL_REFRESHLOGGER`, `LOG_LEVEL_IMPORTLOGGER`, `LOG_LEVEL_SCHEDULELOGGER`, `LOG_LEVEL_SCHEDULEPROCESSORLOGGER`, `LOG_LEVEL_SCHEDULERUNLOGGER`, `LOG_LEVEL_TASKIDLINKLOGGER`, `LOG_LEVEL_TASKNAMELINKLOGGER`, `LOG_LEVEL_TASKLOGGER` | Set each logger's level, typically `DEBUG`, `INFO`, `WARNING`, or `ERROR` (default `INFO`) |
| `DEST_DIR` *(optional)* | Temporary destination for downloaded remote schedules; defaults to the application's `working` directory |

The application reads database connection values from the environment (or `.env`). Schedule-specific settings, including file path, worksheet, part-number cell, date offset, and delimiters, come from active records in `tblLinkedTableNames`. For SharePoint schedules, set the record's remote flag and use its SharePoint sharing URL as `FilePath`; the downloaded local path is assigned to `ScheduleInfo.file_path` while that schedule is being processed.

## Run

From the repository root, with the environment and configuration set:

```powershell
python ScheduleDateRefresher.py
```

The program processes eligible schedule runs for the configured site, reads active Excel schedules, updates task dates and link records, and logs to `ScheduleRefreshLog.txt`. It requires a working SQL Server connection and may write run, task, and schedule-log records to that database.

## Tests

Run the test suite with:

```powershell
python -m pytest Test
```

Some tests exercise real Excel files or SQL Server data, so configure the required database and Excel environment before running the full suite.
