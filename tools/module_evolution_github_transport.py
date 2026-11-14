"""Bounded HTTPS GitHub Actions API transport.

Requires an explicitly supplied read-only token; never prints it. Signed
artifact redirects are followed without forwarding the GitHub bearer token.
No environment credential discovery, workflow permissions, or state writes.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from module_evolution_authenticated_recovery import fetch_and_recover, MAX_ARCHIVE

API = "https://api.github.com"
MAX_METADATA = 2 * 1024 * 1024


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def _url(path):
    if not isinstance(path, str) or not path.startswith("/repos/") or "://" in path or "\\" in path:
        raise ValueError("invalid GitHub API path")
    return API + path


def _read_bounded(response, limit):
    declared = response.headers.get("Content-Length")
    if declared is not None and int(declared) > limit:
        raise ValueError("response exceeds limit")
    data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("response exceeds limit")
    return data


def api_get(path, token, opener=None):
    opener = opener or urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(_url(path), headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "nexus-module-recovery"
    })
    with opener.open(req, timeout=20) as response:
        if response.status != 200:
            raise ValueError("unexpected API response")
        return json.loads(_read_bounded(response, MAX_METADATA))


def archive_get(path, token, opener=None):
    opener = opener or urllib.request.build_opener(NoRedirect)
    req = urllib.request.Request(_url(path), headers={
        "Authorization": "Bearer " + token,
        "Accept": "application/vnd.github+json",
        "User-Agent": "nexus-module-recovery"
    })
    try:
        response = opener.open(req, timeout=20)
    except urllib.error.HTTPError as exc:
        if exc.code not in (302, 303, 307, 308):
            raise
        location = exc.headers.get("Location")
    else:
        with response:
            if response.status != 200:
                raise ValueError("unexpected archive API response")
            return _read_bounded(response, MAX_ARCHIVE)
    if not location:
        raise ValueError("missing archive redirect")
    parsed = urllib.parse.urlsplit(location)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("invalid archive redirect")
    allowed_hosts = ("objects.githubusercontent.com", "pipelines.actions.githubusercontent.com",
                     "productionresultssa0.blob.core.windows.net")
    if parsed.hostname not in allowed_hosts:
        raise ValueError("untrusted artifact redirect host")
    # Token-free request to the signed artifact URL. Do not reuse API headers.
    download = urllib.request.Request(location, headers={"User-Agent": "nexus-module-recovery"})
    with urllib.request.build_opener(NoRedirect).open(download, timeout=20) as response:
        if response.status != 200:
            raise ValueError("unexpected archive download response")
        return _read_bounded(response, MAX_ARCHIVE)


def recover_run(run_id, token):
    """Retrieve and validate a known run. No automatic run selection."""
    return fetch_and_recover(run_id, token, api_get, archive_get)
