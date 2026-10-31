"""CP04 no-credential egress probe. Observations alone never prove enforcement.

Run only inside a separately provisioned, independently controlled test boundary.
Never pass provider credentials. Endpoints are public, non-mutating test sites.
"""
import json
import socket
import sys
import urllib.error
import urllib.request

APPROVED = "https://example.com/"
DENIED = "https://example.org/"


def request(url):
    # No redirects, ambient proxy variables, credentials or user-provided URLs.
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler({}),
        _NoRedirect(),
    )
    try:
        with opener.open(urllib.request.Request(url, method="HEAD"), timeout=5) as response:
            return {"reachable": True, "http_status": response.status}
    except urllib.error.HTTPError as exc:
        # A received HTTP response (including 4xx/5xx) proves reachability.
        return {"reachable": True, "http_status": exc.code}
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return {"reachable": False, "error_type": type(exc).__name__}


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def direct_ip_probe():
    # Documentation address, not a provider or private service.
    try:
        with socket.create_connection(("192.0.2.1", 443), timeout=2):
            return {"reachable": True}
    except OSError as exc:
        return {"reachable": False, "error_type": type(exc).__name__}


def evaluate(approved, denied, direct_ip):
    """A failed request alone is never proof of network-policy enforcement."""
    return {
        "approved_reachable": approved["reachable"],
        "denied_unreachable": not denied["reachable"],
        "direct_ip_unreachable": not direct_ip["reachable"],
        "network_enforcement_proven": False,
        "policy_log_verified": False,
        "verdict": "OBSERVATION_ONLY_REQUIRES_INDEPENDENT_POLICY_EVIDENCE",
    }


def main():
    approved = request(APPROVED)
    denied = request(DENIED)
    direct_ip = direct_ip_probe()
    print(json.dumps({
        "schema_version": 1,
        "probe": "CP04_NO_CREDENTIAL_EGRESS_OBSERVATION",
        "approved": {"destination": "example.com", **approved},
        "denied": {"destination": "example.org", **denied},
        "direct_ip": direct_ip,
        "assessment": evaluate(approved, denied, direct_ip),
    }, sort_keys=True))
    # Never report acceptance from application observations.
    return 0


if __name__ == "__main__":
    sys.exit(main())
