# Schedule Date Refresher

Schedule Date Refresher reads active Excel schedules configured for a site, matches schedule entries to tasks in SQL Server, and updates task due dates and schedule/task links. It also records schedule-run status and logs processing results.

## Requirements

- Windows
- Python 3.10 or later
- Microsoft Excel desktop (the schedules are read through `xlwings`)
- Access to the SQL Server database and the tables, views, and stored procedures used by the application
- Python packages: `psutil`, `pymssql`, `python-dateutil`, `python-dotenv`, `pywin32`, and `xlwings`

## Setup

1. Clone the repository and create/activate a Python virtual environment.
2. Install the packages listed above. To run the tests, also install `pytest`.
3. Create a `.env` file in the repository root with the database connection settings:

   ```dotenv
   DB_SERVER=your-sql-server
   DB_USER=your-database-user
   DB_PASSWORD=your-database-password
   DB_NAME=your-database-name
   ```

   Add the site and run settings to the same file (see Configuration below). Keep credentials private; do not commit `.env`.
4. Set the target site and run behavior in `.env`. The active schedules, Excel file paths, sheet names, and cell layouts are read from SQL Server.
5. Ensure the configured Excel files are accessible to the Windows account running the program.

## Configuration

Settings are read from environment variables, loaded from `.env` in the application directory.

| Variable | Purpose |
| --- | --- |
| `SITE` | SQL Server site ID to process |
| `AUTOMATED_USER_ID` | Employee number used for automated task updates |
| `RUN_LOCAL` | `1` creates a local run entry and waits for confirmation before exit; `0` processes the scheduled run and closes Excel if Excel is already running |
| `AUTO_NOT_SCHEDULED` | `1` enables marking tasks not represented in schedules as "Not Scheduled" when task link records were found |
| `LOG_LEVEL_<LOGGERNAME>` | `DEBUG` or `INFO` per logger, e.g. `LOG_LEVEL_TASKLOGGER` (default `INFO`) |

The application reads database connection values from the environment (or `.env`). Schedule-specific settings, including file path, worksheet, part-number cell, date offset, and delimiters, come from active records in `tblLinkedTableNames`.

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
