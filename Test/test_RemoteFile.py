import os
import pytest
from pathlib import Path
from types import SimpleNamespace

import RemoteFile
import Schedule
from ScheduleInfo import ScheduleInfo


def test_download_uses_graph_client_credentials_and_configured_destination(monkeypatch, tmp_path):
    settings = {
        "CLIENT_ID": "client-id",
        "CLIENT_SECRET": "client-secret",
        "TENANT_ID": "tenant-id",
        "DEST_DIR": str(tmp_path),
    }
    monkeypatch.setattr(RemoteFile.Config, "get_env_value", lambda key, default="": settings.get(key, default))
    monkeypatch.setattr(RemoteFile, "_MSAL_APPLICATION", None)

    class FakeApplication:
        def __init__(self, client_id, client_credential, authority):
            assert client_id == "client-id"
            assert client_credential == "client-secret"
            assert authority == "https://login.microsoftonline.com/tenant-id"

        def acquire_token_for_client(self, scopes):
            assert scopes == ["https://graph.microsoft.com/.default"]
            return {"access_token": "access-token"}
    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def raise_for_status(self):
            pass

        def iter_content(self, chunk_size):
            yield b"workbook"

    requests = {}

    def fake_get(url, headers, stream, timeout):
        requests.update(url=url, headers=headers, stream=stream, timeout=timeout)
        return FakeResponse()

    monkeypatch.setattr(RemoteFile.msal, "ConfidentialClientApplication", FakeApplication)
    monkeypatch.setattr(RemoteFile.requests, "get", fake_get)
    share_url = (
        "https://cretexcompanies.sharepoint.com/:x:/r/sites/RMS-Additive-Shared_Files/"
        "_layouts/15/Doc.aspx?sourcedoc=%7B0BAD2D8D-69C8-4A4C-8C45-9E86779A2D89%7D"
        "&file=Additive%20Mill%20SCHEDULE%201.xlsm&action=default&mobileredirect=true"
        "&wdwpf=doclib-c"
    )

    local_path = RemoteFile.download_to_working_dir(share_url)

    assert os.path.dirname(local_path) == str(tmp_path)
    assert os.path.basename(local_path) == "Additive Mill SCHEDULE 1.xlsm"
    assert Path(local_path).read_bytes() == b"workbook"
    assert requests["url"] == (
        f"{RemoteFile.GRAPH_SHARES_URL}/{RemoteFile._get_share_id(share_url)}/driveItem/content"
    )
    assert requests["headers"] == {"Authorization": "Bearer access-token"}


def test_remote_schedule_info_uses_downloaded_local_path(monkeypatch, tmp_path):
    local_path = str(tmp_path / "schedule.xlsm")
    with open(local_path, "wb") as schedule_file:
        schedule_file.write(b"workbook")
    monkeypatch.setattr(Schedule.RemoteFile, "download_to_working_dir", lambda url: local_path)
    monkeypatch.setattr(Schedule.RemoteFile, "delete_local_file", lambda path: None)

    class FakeRange:
        def __init__(self, value, row=1):
            self.value = value
            self.row = row

        def offset(self, rows, columns):
            return FakeRange("COMP DATE" if columns else self.value, self.row + rows)

        def end(self, direction):
            return self

    class FakeSheet:
        used_range = SimpleNamespace(rows=SimpleNamespace(count=1))

        def range(self, address):
            return FakeRange("PART #" if address == "A1" else None)

    class FakeWorkbook:
        sheets = {"Schedule": FakeSheet()}

        def close(self):
            pass

    class FakeExcelApplication:
        def quit(self):
            pass

    monkeypatch.setattr(Schedule.xlwings, "App", lambda visible: FakeExcelApplication())
    monkeypatch.setattr(
        Schedule.xlwings,
        "Book",
        lambda path, update_links, read_only: FakeWorkbook() if path == local_path else None,
    )
    monkeypatch.setattr(Schedule.RefreshLogger, "get_logger", lambda *_args, **_kwargs: SimpleNamespace(
        debug=lambda *args: None, error=lambda *args, **kwargs: None
    ))
    info = ScheduleInfo(
        schedule_id=1,
        is_active=True,
        site_id=1,
        import_name="Test schedule",
        file_path="https://example.sharepoint.com/schedule.xlsm",
        sheet_name="Schedule",
        starting_cell_address="A1",
        completion_date_cell_offset=1,
        machine_name_offset_left=0,
        machine_name_offset_up=0,
        task_name_delimiter="PART #",
        completion_date_delimiter="COMP DATE",
        do_part_name_trimming=False,
        is_remote=True,
    )

    schedule = Schedule.Schedule(info)

    assert info.file_path == local_path
    schedule.close()


@pytest.mark.skipif(
    not RemoteFile.Config.get_env_value("TEST_REMOTE_URL"),
    reason="Set TEST_REMOTE_URL in .env to run the live SharePoint download test.",
)
def test_live_download_from_sharepoint(monkeypatch, tmp_path):
    url = RemoteFile.Config.get_env_value("TEST_REMOTE_URL")
    monkeypatch.setattr(RemoteFile.Config, "get_env_value", (
        lambda key, default="", _orig=RemoteFile.Config.get_env_value:
        str(tmp_path) if key == "DEST_DIR" else _orig(key, default)
    ))

    local_path = RemoteFile.download_to_working_dir(url)

    assert os.path.dirname(local_path) == str(tmp_path)
    assert Path(local_path).stat().st_size > 0


@pytest.mark.skipif(
    not RemoteFile.Config.get_env_value("CLIENT_ID"),
    reason="Microsoft Graph credentials not configured in .env",
)
def test_live_fallback_recovery_when_sharing_id_is_invalid(monkeypatch, tmp_path):
    monkeypatch.setattr(RemoteFile.Config, "get_env_value", (
        lambda key, default="", _orig=RemoteFile.Config.get_env_value:
        str(tmp_path) if key == "DEST_DIR" else _orig(key, default)
    ))

    # A URL with an invalid/outdated GUID that fails on sharing endpoint
    broken_guid_url = (
        "https://cretexcompanies.sharepoint.com/:x:/r/sites/RMS-Additive-Shared_Files/"
        "_layouts/15/Doc.aspx?sourcedoc=%7B0BAD2D8D-69C8-4A4C-8C45-9E86779A2D89%7D"
        "&file=Additive%20Mill%20SCHEDULE%201.xlsm&action=default&mobileredirect=true&wdwpf=doclib-c"
    )

    local_path = RemoteFile.download_to_working_dir(broken_guid_url)

    assert os.path.dirname(local_path) == str(tmp_path)
    assert os.path.basename(local_path) == "Additive Mill SCHEDULE 1.xlsm"
    assert Path(local_path).stat().st_size > 0