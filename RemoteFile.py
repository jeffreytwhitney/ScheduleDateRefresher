import base64
import logging
import os
import re
import sys
from urllib.parse import parse_qs, quote, unquote, urlparse

import msal
import requests

import Config
import RefreshLogger

WORKING_DIR_NAME = "working"
GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
GRAPH_SHARES_URL = f"{GRAPH_BASE_URL}/shares"
_MSAL_APPLICATION = None
_MSAL_APPLICATION_CONFIG = None


def _get_logger() -> logging.Logger:
    return RefreshLogger.get_logger("scheduleLogger")


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


def _parse_sharepoint_url(url: str) -> tuple[str, str, str | None]:
    """Extract (hostname, site_path, relative_file_path) from a SharePoint URL."""
    parsed = urlparse(url)
    hostname = parsed.netloc
    unquoted_path = unquote(parsed.path)

    match = re.search(r"(/(?:teams|sites)/[^/]+)(.*)$", unquoted_path, re.IGNORECASE)
    if match:
        site_path = match.group(1)
        sub_path = match.group(2).lstrip("/")
        if not sub_path or sub_path.lower().startswith("_layouts") or sub_path.lower().startswith(":"):
            return hostname, site_path, None
        return hostname, site_path, sub_path
    return hostname, "", None


def _download_stream(source_url: str, headers: dict | None, destination_path: str) -> None:
    req_headers = headers if headers else {}
    with requests.get(source_url, headers=req_headers, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(destination_path, "wb") as output_file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    output_file.write(chunk)


def _resolve_and_download_by_path(url: str, token: str, destination_path: str) -> bool:
    """Attempt download using direct site and file path."""
    hostname, site_path, relative_file_path = _parse_sharepoint_url(url)
    if not (hostname and site_path and relative_file_path):
        return False

    doc_path = re.sub(r"^Shared Documents/", "", relative_file_path, flags=re.IGNORECASE)
    encoded_item_path = quote(doc_path.strip("/"))

    headers = {"Authorization": f"Bearer {token}"}
    site_lookup_url = f"{GRAPH_BASE_URL}/sites/{hostname}:{site_path}:"
    site_res = requests.get(site_lookup_url, headers=headers, timeout=30)
    if not site_res.ok:
        return False

    site_id = site_res.json().get("id")
    if not site_id:
        return False

    content_url = f"{GRAPH_BASE_URL}/sites/{site_id}/drive/root:/{encoded_item_path}:/content"
    try:
        _download_stream(content_url, headers, destination_path)
        return True
    except Exception:
        return False


def _resolve_and_download_by_share_link(url: str, token: str, destination_path: str) -> bool:
    """Attempt download using Graph share ID."""
    headers = {"Authorization": f"Bearer {token}"}
    share_id = _get_share_id(url)
    graph_url = f"{GRAPH_SHARES_URL}/{share_id}/driveItem/content"
    try:
        _download_stream(graph_url, headers, destination_path)
        return True
    except Exception:
        return False


def _recover_by_site_filename_search(url: str, token: str, file_name: str, destination_path: str) -> bool:
    """Fallback: find file on SharePoint site by filename and download."""
    logger = _get_logger()
    hostname, site_path, _ = _parse_sharepoint_url(url)
    if not (hostname and site_path):
        return False

    headers = {"Authorization": f"Bearer {token}"}
    site_lookup_url = f"{GRAPH_BASE_URL}/sites/{hostname}:{site_path}:"
    site_res = requests.get(site_lookup_url, headers=headers, timeout=30)
    if not site_res.ok:
        return False

    site_id = site_res.json().get("id")
    if not site_id:
        return False

    lists_res = requests.get(f"{GRAPH_BASE_URL}/sites/{site_id}/lists", headers=headers, timeout=30)
    if not lists_res.ok:
        return False

    target_name_clean = file_name.strip().lower()
    for doc_list in lists_res.json().get("value", []):
        list_id = doc_list.get("id")
        items_url = f"{GRAPH_BASE_URL}/sites/{site_id}/lists/{list_id}/items?expand=driveItem&$top=200"
        items_res = requests.get(items_url, headers=headers, timeout=30)
        if not items_res.ok:
            continue

        for item in items_res.json().get("value", []):
            drive_item = item.get("driveItem")
            if not drive_item:
                continue

            item_name = drive_item.get("name", "")
            if item_name.strip().lower() == target_name_clean:
                download_url = drive_item.get("@microsoft.graph.downloadUrl")
                if download_url:
                    logger.warning(
                        f"Auto-recovered remote schedule for '{file_name}' from library '{doc_list.get('name')}'"
                    )
                    _download_stream(download_url, None, destination_path)
                    return True
    return False


def download_to_working_dir(url: str) -> str:
    """Download a SharePoint file through Microsoft Graph with automatic recovery."""
    destination_dir = _get_destination_directory()
    os.makedirs(destination_dir, exist_ok=True)

    file_name = _get_file_name(url)
    local_path = os.path.join(destination_dir, file_name)
    token = _get_access_token()

    try:
        # Strategy 1: Direct path download if clean path URL is provided
        if _resolve_and_download_by_path(url, token, local_path):
            return local_path

        # Strategy 2: Direct share link download
        if _resolve_and_download_by_share_link(url, token, local_path):
            return local_path

        # Strategy 3: Auto-recovery search by filename on the site
        if _recover_by_site_filename_search(url, token, file_name, local_path):
            return local_path

        raise FileNotFoundError(f"Could not resolve or download file from URL: {url}")
    except Exception:
        delete_local_file(local_path)
        raise


def delete_local_file(path: str) -> None:
    try:
        if path and os.path.isfile(path):
            os.remove(path)
    except OSError:
        pass
