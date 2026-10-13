import base64
import os
import sys
from urllib.parse import parse_qs, unquote, urlparse

import msal
import requests

import Config

WORKING_DIR_NAME = "working"
GRAPH_SHARES_URL = "https://graph.microsoft.com/v1.0/shares"
_MSAL_APPLICATION = None
_MSAL_APPLICATION_CONFIG = None


def _get_current_directory() -> str:
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def _get_destination_directory() -> str:
    destination = Config.get_env_value("DEST_DIR")
    if not destination:
        destination = os.path.join(_get_current_directory(), WORKING_DIR_NAME)
    elif not os.path.isabs(destination):
        destination = os.path.join(_get_current_directory(), destination)
    return destination


def _get_access_token() -> str:
    global _MSAL_APPLICATION, _MSAL_APPLICATION_CONFIG

    client_id = Config.get_env_value("CLIENT_ID")
    client_secret = Config.get_env_value("CLIENT_SECRET")
    tenant_id = Config.get_env_value("TENANT_ID")
    if not client_id:
        raise ValueError("CLIENT_ID must be configured in .env to download remote schedules.")
    if not client_secret:
        raise ValueError("CLIENT_SECRET must be configured in .env to download remote schedules.")
    if not tenant_id:
        raise ValueError("TENANT_ID must be configured in .env to download remote schedules.")

    authority = f"https://login.microsoftonline.com/{tenant_id}"
    application_config = (client_id, client_secret, authority)
    if _MSAL_APPLICATION is None or _MSAL_APPLICATION_CONFIG != application_config:
        _MSAL_APPLICATION = msal.ConfidentialClientApplication(
            client_id, client_credential=client_secret, authority=authority)
        _MSAL_APPLICATION_CONFIG = application_config

    # App-only auth always uses the .default scope; permissions are granted in Azure.
    result = _MSAL_APPLICATION.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    access_token = result.get("access_token")
    if not access_token:
        details = result.get("error_description") or result.get("error") or result
        raise RuntimeError(f"Microsoft sign-in failed: {details}")
    return access_token

def _get_share_id(url: str) -> str:
    encoded_url = base64.urlsafe_b64encode(url.encode("utf-8")).decode("ascii").rstrip("=")
    return f"u!{encoded_url}"


def _get_file_name(url: str) -> str:
    query_file = parse_qs(urlparse(url).query).get("file")
    if query_file and query_file[0]:
        return os.path.basename(query_file[0])
    path_file = os.path.basename(unquote(urlparse(url).path))
    return path_file if path_file and path_file.lower() != "doc.aspx" else "schedule.xlsx"


def download_to_working_dir(url: str) -> str:
    """Download a SharePoint sharing URL through Microsoft Graph and return its local path."""
    destination_dir = _get_destination_directory()
    os.makedirs(destination_dir, exist_ok=True)

    local_path = os.path.join(destination_dir, _get_file_name(url))
    share_id = _get_share_id(url)
    graph_url = f"{GRAPH_SHARES_URL}/{share_id}/driveItem/content"

    try:
        headers = {"Authorization": f"Bearer {_get_access_token()}"}
        with requests.get(graph_url, headers=headers, stream=True, timeout=60) as response:
            response.raise_for_status()
            with open(local_path, "wb") as output_file:
                for chunk in response.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        output_file.write(chunk)
    except Exception:
        delete_local_file(local_path)
        raise

    return local_path


def delete_local_file(path: str) -> None:
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
