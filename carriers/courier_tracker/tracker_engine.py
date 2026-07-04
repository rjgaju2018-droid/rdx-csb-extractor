"""
Multi-Courier Anti-Block Tracking Engine v2.0
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Couriers: FedEx | DHL | UPS | Aramex | Shiprocket | OnPoint | ShipGlobal | Xindus
Features:
  ✅ 3-layer fallback (API → Web Scrape → Public Endpoint)
  ✅ Smart rate limiting per courier (no blocks)
  ✅ Rotating User-Agents
  ✅ Retry with exponential backoff
  ✅ 30 concurrent threads (300 shipments fast)
  ✅ Session pooling (reuse connections)
  ✅ Auto courier detection
"""

import requests
import threading
import time
import json
import re
import random
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict

# ─── USER AGENT POOL ────────────────────────────────────────────────
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.0.0",
]

def random_ua():
    return random.choice(USER_AGENTS)

def base_headers(extra=None):
    h = {
        "User-Agent": random_ua(),
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Cache-Control": "no-cache",
    }
    if extra:
        h.update(extra)
    return h


# ─── RATE LIMITER (per courier) ─────────────────────────────────────
class RateLimiter:
    """Prevents courier APIs from blocking due to too-fast requests"""
    def __init__(self, calls_per_second=5):
        self._min_interval = 1.0 / calls_per_second
        self._last_call    = 0
        self._lock         = threading.Lock()

    def wait(self):
        with self._lock:
            now     = time.time()
            elapsed = now - self._last_call
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed + random.uniform(0.01, 0.05))
            self._last_call = time.time()


# ─── SESSION POOL ───────────────────────────────────────────────────
class SessionPool:
    """Reuses HTTP sessions for better performance"""
    def __init__(self, size=10):
        self._sessions = []
        self._lock     = threading.Lock()
        for _ in range(size):
            s = requests.Session()
            s.headers.update(base_headers())
            adapter = requests.adapters.HTTPAdapter(
                max_retries=requests.adapters.Retry(
                    total=2, backoff_factor=0.3,
                    status_forcelist=[500, 502, 503, 504],
                )
            )
            s.mount("https://", adapter)
            s.mount("http://",  adapter)
            self._sessions.append(s)

    def get(self):
        with self._lock:
            return random.choice(self._sessions)


_session_pool = SessionPool(10)


# ─── RESULT OBJECT ──────────────────────────────────────────────────
class TrackResult:
    def __init__(self, tracking_no, courier):
        self.tracking_no = tracking_no
        self.courier     = courier
        self.status      = "Pending"
        self.location    = "-"
        self.description = "-"
        self.timestamp   = "-"
        self.delivered   = False
        self.error       = None
        self.events      = []
        self.eta         = "-"
        self.method_used = "-"   # API / Scrape / Public

    def to_dict(self):
        return {
            "Tracking No":   self.tracking_no,
            "Courier":       self.courier,
            "Status":        self.status,
            "Location":      self.location,
            "Description":   self.description,
            "Last Update":   self.timestamp,
            "ETA":           self.eta,
            "Delivered":     "Yes" if self.delivered else "No",
            "Method":        self.method_used,
            "Error":         self.error or "",
        }


# ─── BASE TRACKER ───────────────────────────────────────────────────
class BaseTracker:
    TIMEOUT      = 18
    MAX_RETRIES  = 3
    RETRY_DELAYS = [1, 2, 4]   # Exponential backoff

    def __init__(self):
        self.rate_limiter = RateLimiter(calls_per_second=4)

    def track(self, tracking_no: str) -> TrackResult:
        result = TrackResult(tracking_no, self.name)
        errors = []

        # Layer 1: Official API
        if hasattr(self, "_api_fetch"):
            for attempt in range(self.MAX_RETRIES):
                try:
                    self.rate_limiter.wait()
                    self._api_fetch(result)
                    if result.status not in ("Pending", "Error"):
                        result.method_used = "API"
                        return result
                except requests.exceptions.Timeout:
                    errors.append(f"API timeout (attempt {attempt+1})")
                except requests.exceptions.ConnectionError as e:
                    errors.append(f"API connection error: {str(e)[:50]}")
                except Exception as e:
                    errors.append(f"API error: {str(e)[:60]}")
                if attempt < self.MAX_RETRIES - 1:
                    time.sleep(self.RETRY_DELAYS[attempt])

        # Layer 2: Web Scrape fallback
        if hasattr(self, "_scrape_fetch"):
            for attempt in range(2):
                try:
                    self.rate_limiter.wait()
                    self._scrape_fetch(result)
                    if result.status not in ("Pending", "Error"):
                        result.method_used = "Scrape"
                        return result
                except Exception as e:
                    errors.append(f"Scrape error: {str(e)[:60]}")
                if attempt < 1:
                    time.sleep(1.5)

        # Layer 3: Public endpoint fallback
        if hasattr(self, "_public_fetch"):
            try:
                self.rate_limiter.wait()
                self._public_fetch(result)
                if result.status not in ("Pending", "Error"):
                    result.method_used = "Public"
                    return result
            except Exception as e:
                errors.append(f"Public error: {str(e)[:60]}")

        # All layers failed
        result.status    = "Check Website"
        result.error     = " | ".join(errors[-2:]) if errors else "All methods failed"
        result.method_used = "Failed"
        return result

    def _get(self, url, **kwargs):
        kwargs.setdefault("timeout", self.TIMEOUT)
        kwargs.setdefault("headers", base_headers())
        return _session_pool.get().get(url, **kwargs)

    def _post(self, url, **kwargs):
        kwargs.setdefault("timeout", self.TIMEOUT)
        kwargs.setdefault("headers", base_headers())
        return _session_pool.get().post(url, **kwargs)


# ─── FEDEX ──────────────────────────────────────────────────────────
class FedExTracker(BaseTracker):
    name = "FedEx"

    def __init__(self, api_key="", secret_key=""):
        super().__init__()
        self.api_key    = api_key
        self.secret_key = secret_key
        self._token     = None
        self._token_exp = 0
        self._lock      = threading.Lock()

    def _get_token(self):
        with self._lock:
            if self._token and time.time() < self._token_exp:
                return self._token
            if not self.api_key:
                return None
            r = self._post(
                "https://apis.fedex.com/oauth/token",
                data={"grant_type": "client_credentials",
                      "client_id": self.api_key,
                      "client_secret": self.secret_key},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            if r.ok:
                d = r.json()
                self._token     = d.get("access_token")
                self._token_exp = time.time() + d.get("expires_in", 3600) - 120
                return self._token
        return None

    def _api_fetch(self, result: TrackResult):
        token = self._get_token()
        if not token:
            return
        r = self._post(
            "https://apis.fedex.com/track/v1/trackingnumbers",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"trackingInfo": [{"trackingNumberInfo": {"trackingNumber": result.tracking_no}}],
                  "includeDetailedScans": True},
        )
        if r.status_code == 429:
            time.sleep(5)
            raise Exception("Rate limited")
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        data = r.json()
        pkg  = data["output"]["completeTrackResults"][0]["trackResults"][0]
        self._parse_fedex(result, pkg)

    def _scrape_fetch(self, result: TrackResult):
        """Scrape FedEx tracking page"""
        url = f"https://www.fedex.com/fedextrack/?action=track&trackingnumber={result.tracking_no}&cntry_code=in"
        r = self._get(url, headers=base_headers({
            "Referer": "https://www.fedex.com/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }))
        if r.ok and "tracking" in r.text.lower():
            # Extract status from meta/json in page
            match = re.search(r'"statusDescription"\s*:\s*"([^"]+)"', r.text)
            if match:
                result.status      = match.group(1)
                result.description = result.status
                loc = re.search(r'"city"\s*:\s*"([^"]+)"', r.text)
                if loc:
                    result.location = loc.group(1)
                result.delivered = "delivered" in result.status.lower()

    def _public_fetch(self, result: TrackResult):
        """FedEx public tracking API (no auth needed for basic)"""
        r = self._get(
            f"https://www.fedex.com/trackingCal/track",
            params={"tracknumbers": result.tracking_no, "action": "trackpackages",
                    "format": "json", "version": "99", "locale": "en_IN"},
            headers=base_headers({"X-Requested-With": "XMLHttpRequest",
                                   "Referer": "https://www.fedex.com/"}),
        )
        if r.ok:
            try:
                d = r.json()
                pkgs = d.get("TrackPackagesResponse", {}).get("packageList", [])
                if pkgs:
                    p = pkgs[0]
                    result.status      = p.get("keyStatus", "Unknown")
                    result.description = p.get("statusDescription", result.status)
                    result.location    = p.get("lastLocation", {}).get("locationDesc", "-")
                    result.timestamp   = p.get("lastEventTime", "-")
                    result.delivered   = "delivered" in result.status.lower()
                    result.eta         = p.get("promisedDelivery", "-")
            except Exception:
                pass

    def _parse_fedex(self, result, pkg):
        result.status      = pkg.get("latestStatusDetail", {}).get("description", "Unknown")
        result.description = result.status
        loc = pkg.get("latestStatusDetail", {}).get("scanLocation", {})
        result.location    = f"{loc.get('city','')}, {loc.get('countryCode','')}".strip(", ")
        dts = pkg.get("dateAndTimes", [])
        if dts:
            result.timestamp = dts[0].get("dateTime", "-")[:16].replace("T", " ")
        result.delivered   = "delivered" in result.status.lower()
        scans = pkg.get("scanEvents", [])
        result.events      = [
            f"{e.get('date','')[:16].replace('T',' ')} | {e.get('eventDescription','')} | {e.get('scanLocation',{}).get('city','')}"
            for e in scans[:12]
        ]


# ─── DHL ────────────────────────────────────────────────────────────
class DHLTracker(BaseTracker):
    name = "DHL"

    def __init__(self, api_key=""):
        super().__init__()
        self.api_key = api_key

    def _api_fetch(self, result: TrackResult):
        if not self.api_key:
            return
        r = self._get(
            "https://api-eu.dhl.com/track/shipments",
            params={"trackingNumber": result.tracking_no, "language": "en"},
            headers=base_headers({"DHL-API-Key": self.api_key}),
        )
        if r.status_code == 429:
            time.sleep(6); raise Exception("Rate limited")
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        self._parse_dhl(result, r.json())

    def _scrape_fetch(self, result: TrackResult):
        """DHL public JSON endpoint — no auth needed"""
        r = self._get(
            f"https://api-test.dhl.com/track/shipments",
            params={"trackingNumber": result.tracking_no},
            headers=base_headers({
                "DHL-API-Key": "demo-key",
                "Referer": "https://www.dhl.com/",
            }),
        )
        if r.ok:
            self._parse_dhl(result, r.json())
            return

        # Fallback: DHL Express tracking endpoint
        r2 = self._get(
            "https://www.dhl.com/utapi",
            params={"trackingNumber": result.tracking_no, "language": "en",
                    "requiredFields": "details,events,description"},
            headers=base_headers({"Referer": "https://www.dhl.com/en/express/tracking.html"}),
        )
        if r2.ok:
            try:
                data = r2.json()
                self._parse_dhl(result, data)
            except Exception:
                pass

    def _public_fetch(self, result: TrackResult):
        """DHL Parcel tracking (works for many DHL shipments)"""
        r = self._get(
            f"https://www.dhl.com/en/express/tracking.spage",
            params={"AWB": result.tracking_no},
            headers=base_headers({"Accept": "text/html", "Referer": "https://www.dhl.com/"}),
        )
        if r.ok:
            # Extract from HTML
            m_status = re.search(r'class="status-label[^"]*"[^>]*>([^<]+)<', r.text)
            m_loc    = re.search(r'"location"\s*:\s*"([^"]+)"', r.text)
            if m_status:
                result.status      = m_status.group(1).strip()
                result.description = result.status
                result.location    = m_loc.group(1) if m_loc else "-"
                result.delivered   = "delivered" in result.status.lower()

    def _parse_dhl(self, result, data):
        ships = data.get("shipments", [])
        if not ships:
            return
        ship   = ships[0]
        events = ship.get("events", [])
        latest = events[0] if events else {}
        result.status      = ship.get("status", {}).get("description", "Unknown")
        result.description = latest.get("description", result.status)
        result.location    = latest.get("location", {}).get("address", {}).get("addressLocality", "-")
        result.timestamp   = latest.get("timestamp", "-")[:16].replace("T", " ")
        result.delivered   = ship.get("status", {}).get("statusCode", "") == "delivered"
        result.events      = [
            f"{e.get('timestamp','')[:16].replace('T',' ')} | {e.get('description','')} | {e.get('location',{}).get('address',{}).get('addressLocality','')}"
            for e in events[:12]
        ]


# ─── UPS ────────────────────────────────────────────────────────────
class UPSTracker(BaseTracker):
    name = "UPS"

    def __init__(self, api_key="", client_id="", client_secret=""):
        super().__init__()
        self.api_key       = api_key
        self.client_id     = client_id
        self.client_secret = client_secret
        self._token        = None
        self._token_exp    = 0
        self._lock         = threading.Lock()

    def _get_token(self):
        with self._lock:
            if self._token and time.time() < self._token_exp:
                return self._token
            if not self.client_id:
                return None
            r = self._post(
                "https://onlinetools.ups.com/security/v1/oauth/token",
                data={"grant_type": "client_credentials"},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                auth=(self.client_id, self.client_secret),
            )
            if r.ok:
                d = r.json()
                self._token     = d.get("access_token")
                self._token_exp = time.time() + int(d.get("expires_in", 3600)) - 120
                return self._token
        return None

    def _api_fetch(self, result: TrackResult):
        token = self._get_token()
        if not token:
            return
        r = self._get(
            f"https://onlinetools.ups.com/api/track/v1/details/{result.tracking_no}",
            headers=base_headers({"Authorization": f"Bearer {token}",
                                   "transId": f"track_{int(time.time())}",
                                   "transactionSrc": "MultiCourierTracker"}),
        )
        if r.status_code == 429:
            time.sleep(8); raise Exception("Rate limited")
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        pkg = r.json()["trackResponse"]["shipment"][0]["package"][0]
        self._parse_ups(result, pkg)

    def _scrape_fetch(self, result: TrackResult):
        """UPS public tracking page JSON"""
        r = self._post(
            "https://www.ups.com/track/api/Track/GetStatus?loc=en_IN",
            json={"Locale": "en_IN", "TrackingNumber": [result.tracking_no]},
            headers=base_headers({
                "Content-Type": "application/json",
                "Referer": "https://www.ups.com/track?loc=en_IN",
                "X-XSRF-TOKEN": "undefined",
            }),
        )
        if r.ok:
            try:
                data  = r.json()
                track = data.get("trackResponse", {}).get("shipment", [{}])[0]
                pkg   = track.get("package", [{}])[0]
                self._parse_ups(result, pkg)
            except Exception:
                pass

    def _public_fetch(self, result: TrackResult):
        r = self._get(
            f"https://www.ups.com/track",
            params={"loc": "en_IN", "tracknum": result.tracking_no, "requester": "ST/trackdetails"},
            headers=base_headers({"Referer": "https://www.ups.com/", "Accept": "text/html"}),
        )
        if r.ok:
            m = re.search(r'"statusDescription"\s*:\s*"([^"]+)"', r.text)
            if m:
                result.status      = m.group(1)
                result.description = result.status
                result.delivered   = "delivered" in result.status.lower()

    def _parse_ups(self, result, pkg):
        acts   = pkg.get("activity", [])
        latest = acts[0] if acts else {}
        result.status      = latest.get("status", {}).get("description", "Unknown")
        result.description = result.status
        loc                = latest.get("location", {}).get("address", {})
        result.location    = f"{loc.get('city','')}, {loc.get('country','')}".strip(", ")
        result.timestamp   = f"{latest.get('date','')} {latest.get('time','')}".strip()
        result.delivered   = "delivered" in result.status.lower()
        result.events      = [
            f"{a.get('date','')} {a.get('time','')} | {a.get('status',{}).get('description','')} | {a.get('location',{}).get('address',{}).get('city','')}"
            for a in acts[:12]
        ]


# ─── ARAMEX ─────────────────────────────────────────────────────────
class AramexTracker(BaseTracker):
    name = "Aramex"

    def __init__(self, username="", password="", account_no="",
                 account_pin="", account_entity="", country_code="IN"):
        super().__init__()
        self.username       = username
        self.password       = password
        self.account_no     = account_no
        self.account_pin    = account_pin
        self.account_entity = account_entity
        self.country_code   = country_code

    def _api_fetch(self, result: TrackResult):
        if not self.username:
            return
        r = self._post(
            "https://ws.aramex.net/ShippingAPI.V2/Tracking/Service_1_0.svc/json/TrackShipments",
            json={
                "ClientInfo": {
                    "UserName": self.username, "Password": self.password,
                    "Version": "v1.0", "AccountNumber": self.account_no,
                    "AccountPin": self.account_pin, "AccountEntity": self.account_entity,
                    "AccountCountryCode": self.country_code,
                },
                "Transaction": {"Reference1": "tracker"},
                "Shipments": {"ShipmentNumber": [result.tracking_no]},
                "GetLastTrackingUpdateOnly": False,
            },
            headers=base_headers({"Content-Type": "application/json"}),
        )
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        data    = r.json()
        results_key = "TrackingResults"
        track   = data.get(results_key, {}).get("KeyValueOfstringArrayOfTrackingResultmFAkxlpY", [])
        if not track:
            raise Exception("No data")
        updates = track[0].get("Value", [])
        if not updates:
            raise Exception("No updates")
        self._parse_aramex(result, updates)

    def _scrape_fetch(self, result: TrackResult):
        """Aramex public tracking"""
        r = self._get(
            f"https://www.aramex.com/us/en/track/results",
            params={"ShipmentNumber": result.tracking_no},
            headers=base_headers({"Referer": "https://www.aramex.com/", "Accept": "text/html"}),
        )
        if r.ok and result.tracking_no in r.text:
            m = re.search(r'class="latest-update[^"]*"[^>]*>([^<]+)<', r.text)
            if m:
                result.status      = m.group(1).strip()
                result.description = result.status
                result.delivered   = "delivered" in result.status.lower()

    def _public_fetch(self, result: TrackResult):
        """Aramex JSON endpoint"""
        r = self._post(
            "https://www.aramex.com/api/track",
            json={"ShipmentNumber": result.tracking_no, "lang": "en"},
            headers=base_headers({"Content-Type": "application/json",
                                   "Referer": "https://www.aramex.com/"}),
        )
        if r.ok:
            try:
                d = r.json()
                updates = d.get("TrackingUpdates", [])
                if updates:
                    self._parse_aramex(result, updates)
            except Exception:
                pass

    def _parse_aramex(self, result, updates):
        latest         = updates[0]
        result.status  = latest.get("UpdateDescription", "Unknown")
        result.location= latest.get("UpdateLocation", "-")
        result.timestamp = str(latest.get("UpdateDateTime", "-"))[:16].replace("T", " ")
        result.description = result.status
        result.delivered = "delivered" in result.status.lower()
        result.events    = [
            f"{str(u.get('UpdateDateTime',''))[:16].replace('T',' ')} | {u.get('UpdateDescription','')} | {u.get('UpdateLocation','')}"
            for u in updates[:12]
        ]


# ─── SHIPROCKET ─────────────────────────────────────────────────────
class ShiprocketTracker(BaseTracker):
    name = "Shiprocket"

    def __init__(self, email="", password=""):
        super().__init__()
        self.email    = email
        self.password = password
        self._token   = None
        self._lock    = threading.Lock()

    def _get_token(self):
        with self._lock:
            if self._token:
                return self._token
            if not self.email:
                return None
            r = self._post(
                "https://apiv2.shiprocket.in/v1/external/auth/login",
                json={"email": self.email, "password": self.password},
                headers=base_headers({"Content-Type": "application/json"}),
            )
            if r.ok:
                self._token = r.json().get("token")
                return self._token
        return None

    def _api_fetch(self, result: TrackResult):
        token = self._get_token()
        if not token:
            return
        r = self._get(
            f"https://apiv2.shiprocket.in/v1/external/courier/track/awb/{result.tracking_no}",
            headers=base_headers({"Authorization": f"Bearer {token}"}),
        )
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        self._parse_shiprocket(result, r.json())

    def _public_fetch(self, result: TrackResult):
        """Shiprocket public tracking page"""
        r = self._get(
            f"https://shiprocket.co/tracking/{result.tracking_no}",
            headers=base_headers({"Accept": "text/html",
                                   "Referer": "https://shiprocket.co/"}),
        )
        if r.ok:
            m_status = re.search(r'"current_status"\s*:\s*"([^"]+)"', r.text)
            m_loc    = re.search(r'"city"\s*:\s*"([^"]+)"', r.text)
            if m_status:
                result.status      = m_status.group(1)
                result.description = result.status
                result.location    = m_loc.group(1) if m_loc else "-"
                result.delivered   = "delivered" in result.status.lower()

    def _parse_shiprocket(self, result, data):
        td    = data.get("tracking_data", {})
        track = td.get("shipment_track", [{}])[0]
        result.status      = track.get("current_status", "Unknown")
        result.location    = track.get("origin", "-")
        result.timestamp   = str(track.get("updated_at", "-"))[:16]
        result.description = result.status
        result.delivered   = "delivered" in result.status.lower()
        acts               = td.get("shipment_track_activities", [])
        result.events      = [
            f"{a.get('date','')} | {a.get('activity','')} | {a.get('location','')}"
            for a in acts[:12]
        ]


# ─── ONPOINT (17TRACK) ──────────────────────────────────────────────
class OnPointTracker(BaseTracker):
    name = "OnPoint"

    def __init__(self, api_key=""):
        super().__init__()
        self.api_key = api_key

    def _api_fetch(self, result: TrackResult):
        if not self.api_key:
            return
        r = self._post(
            "https://api.17track.net/track/v2.2/gettrackinfo",
            json=[{"number": result.tracking_no}],
            headers=base_headers({"17token": self.api_key, "Content-Type": "application/json"}),
        )
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        self._parse_17track(result, r.json())

    def _public_fetch(self, result: TrackResult):
        """17track public endpoint"""
        r = self._post(
            "https://t.17track.net/restapi/track",
            json={"data": [{"num": result.tracking_no}], "guid": "", "timeZoneOffset": 330},
            headers=base_headers({
                "Content-Type": "application/json",
                "Referer": "https://t.17track.net/",
                "Origin":  "https://t.17track.net",
            }),
        )
        if r.ok:
            try:
                d = r.json()
                items = d.get("dat", [{}])[0].get("track", {})
                z1    = items.get("z1", [])
                if z1 and isinstance(z1, list):
                    latest         = z1[0]
                    result.status  = latest.get("z", "Unknown")
                    result.location= latest.get("l", "-")
                    result.timestamp = str(latest.get("a", "-"))[:16]
                    result.description = result.status
                    result.delivered = "delivered" in result.status.lower()
                    result.events    = [
                        f"{str(e.get('a',''))[:16]} | {e.get('z','')} | {e.get('l','')}"
                        for e in z1[:12]
                    ]
            except Exception:
                pass

    def _parse_17track(self, result, data):
        track = data.get("data", {}).get("accepted", [{}])[0]
        info  = track.get("track", {})
        events = info.get("z1", []) if isinstance(info.get("z1"), list) else []
        if not events:
            return
        latest         = events[0]
        result.status  = latest.get("z", "Unknown")
        result.location= latest.get("l", "-")
        result.timestamp = str(latest.get("a", "-"))[:16]
        result.description = result.status
        result.delivered = "delivered" in result.status.lower()
        result.events    = [
            f"{str(e.get('a',''))[:16]} | {e.get('z','')} | {e.get('l','')}"
            for e in events[:12]
        ]


# ─── SHIPGLOBAL ─────────────────────────────────────────────────────
class ShipGlobalTracker(BaseTracker):
    name = "ShipGlobal"

    def __init__(self, api_key=""):
        super().__init__()
        self.api_key = api_key

    def _api_fetch(self, result: TrackResult):
        if not self.api_key:
            return
        r = self._get(
            f"https://app.shipglobal.in/api/tracking/{result.tracking_no}",
            headers=base_headers({"Authorization": f"Bearer {self.api_key}"}),
        )
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        self._parse_sg(result, r.json())

    def _public_fetch(self, result: TrackResult):
        r = self._get(
            f"https://app.shipglobal.in/tracking/{result.tracking_no}",
            headers=base_headers({"Accept": "text/html",
                                   "Referer": "https://shipglobal.in/"}),
        )
        if r.ok:
            m = re.search(r'"status"\s*:\s*"([^"]+)"', r.text)
            if m:
                result.status      = m.group(1)
                result.description = result.status
                result.delivered   = "delivered" in result.status.lower()

    def _parse_sg(self, result, data):
        d      = data.get("data", {})
        events = d.get("events", [])
        latest = events[0] if events else {}
        result.status      = latest.get("status", d.get("status", "Unknown"))
        result.location    = latest.get("location", "-")
        result.timestamp   = str(latest.get("timestamp", "-"))[:16]
        result.description = latest.get("description", result.status)
        result.delivered   = "delivered" in result.status.lower()
        result.events      = [
            f"{str(e.get('timestamp',''))[:16]} | {e.get('description','')} | {e.get('location','')}"
            for e in events[:12]
        ]


# ─── XINDUS ─────────────────────────────────────────────────────────
class XindusTracker(BaseTracker):
    name = "Xindus"

    def __init__(self, api_key="", client_id=""):
        super().__init__()
        self.api_key   = api_key
        self.client_id = client_id

    def _api_fetch(self, result: TrackResult):
        if not self.api_key:
            return
        r = self._get(
            f"https://api.xindus.co/v1/track/{result.tracking_no}",
            headers=base_headers({"x-api-key": self.api_key,
                                   "x-client-id": self.client_id}),
        )
        if not r.ok:
            raise Exception(f"HTTP {r.status_code}")
        self._parse_xindus(result, r.json())

    def _public_fetch(self, result: TrackResult):
        r = self._post(
            "https://xindus.co/api/track",
            json={"awb": result.tracking_no},
            headers=base_headers({"Content-Type": "application/json",
                                   "Referer": "https://xindus.co/"}),
        )
        if r.ok:
            try:
                d = r.json()
                result.status      = d.get("status", "Unknown")
                result.description = d.get("description", result.status)
                result.delivered   = "delivered" in result.status.lower()
            except Exception:
                pass

    def _parse_xindus(self, result, data):
        latest         = data.get("latestEvent", {})
        result.status  = latest.get("status", data.get("status", "Unknown"))
        result.location= latest.get("location", "-")
        result.timestamp = str(latest.get("datetime", "-"))[:16]
        result.description = latest.get("description", result.status)
        result.delivered = "delivered" in result.status.lower()
        result.events    = [
            f"{str(e.get('datetime',''))[:16]} | {e.get('description','')} | {e.get('location','')}"
            for e in data.get("events", [])[:12]
        ]


# ─── AUTO-DETECT COURIER ────────────────────────────────────────────
PATTERNS = [
    ("FedEx",      [r"^\d{12}$", r"^\d{15}$", r"^\d{20}$",
                    r"^96\d{18}$", r"^7489\d{16}$", r"^02\d{18}$"]),
    ("UPS",        [r"^1Z[A-Z0-9]{16}$", r"^T\d{10}$", r"^\d{9}$"]),
    ("DHL",        [r"^JD\d{18}$", r"^\d{10}$", r"^[A-Z]{2}\d{9}[A-Z]{2}$"]),
    ("Aramex",     [r"^\d{11}$", r"^6\d{10}$", r"^AR\d{9,12}$", r"^1\d{10}$"]),
    ("Shiprocket", [r"^SR\d{8,12}$", r"^SRIN\d{6,10}$"]),
    ("OnPoint",    [r"^OP\d{8,12}$", r"^ON\d{10}$"]),
    ("ShipGlobal", [r"^SG[A-Z0-9]{8,12}$", r"^SGI\d{9}$"]),
    ("Xindus",     [r"^XI\d{8,12}$", r"^XD\d{10}$"]),
]

def detect_courier(tracking_no: str) -> str:
    tn = tracking_no.strip().upper()
    for courier, pats in PATTERNS:
        for pat in pats:
            if re.match(pat, tn):
                return courier
    return "Auto"


# ─── TRACKING ENGINE ────────────────────────────────────────────────
class TrackingEngine:
    # Smart thread count — enough for speed, not enough to trigger rate limits
    MAX_WORKERS = 25

    def __init__(self, config: dict):
        c = config
        self.trackers = {
            "FedEx":      FedExTracker(c.get("fedex_api_key",""), c.get("fedex_secret_key","")),
            "DHL":        DHLTracker(c.get("dhl_api_key","")),
            "UPS":        UPSTracker(c.get("ups_api_key",""), c.get("ups_client_id",""), c.get("ups_client_secret","")),
            "Aramex":     AramexTracker(c.get("aramex_username",""), c.get("aramex_password",""),
                                        c.get("aramex_account_no",""), c.get("aramex_account_pin",""),
                                        c.get("aramex_account_entity",""), c.get("aramex_country_code","IN")),
            "Shiprocket": ShiprocketTracker(c.get("shiprocket_email",""), c.get("shiprocket_password","")),
            "OnPoint":    OnPointTracker(c.get("onpoint_api_key","")),
            "ShipGlobal": ShipGlobalTracker(c.get("shipglobal_api_key","")),
            "Xindus":     XindusTracker(c.get("xindus_api_key",""), c.get("xindus_client_id","")),
        }
        # Per-courier semaphores to prevent hammering one courier
        self._semaphores = {name: threading.Semaphore(6) for name in self.trackers}

    def _track_single(self, tracking_no: str, courier: str) -> TrackResult:
        if courier == "Auto":
            courier = detect_courier(tracking_no)
        tracker = self.trackers.get(courier)
        if not tracker:
            # Try all trackers as last resort
            for name, t in self.trackers.items():
                sem = self._semaphores[name]
                with sem:
                    result = t.track(tracking_no)
                if result.status not in ("Pending", "Check Website", "Error"):
                    result.courier = name
                    return result
            r = TrackResult(tracking_no, courier)
            r.status = "Unknown Courier"
            r.error  = f"Could not identify courier for: {tracking_no}"
            return r

        sem = self._semaphores.get(courier, threading.Semaphore(6))
        with sem:
            return tracker.track(tracking_no)

    def track_bulk(self, shipments: list, progress_callback=None,
                   stop_event: threading.Event = None) -> list:
        """
        shipments = [{"tracking_no": "xxx", "courier": "FedEx"}, ...]
        stop_event: set() to cancel mid-tracking
        Returns list of TrackResult
        """
        results   = [None] * len(shipments)
        completed = [0]
        lock      = threading.Lock()

        if stop_event is None:
            stop_event = threading.Event()

        def task(idx, item):
            if stop_event.is_set():
                r = TrackResult(item["tracking_no"], item.get("courier","Auto"))
                r.status = "Cancelled"
                results[idx] = r
                return

            res = self._track_single(item["tracking_no"].strip(), item.get("courier","Auto"))
            results[idx] = res

            with lock:
                completed[0] += 1
                if progress_callback:
                    progress_callback(completed[0], len(shipments), res)

        with ThreadPoolExecutor(max_workers=self.MAX_WORKERS) as exe:
            futs = [exe.submit(task, i, s) for i, s in enumerate(shipments)]
            for f in as_completed(futs):
                try:
                    f.result()
                except Exception:
                    pass

        return [r for r in results if r is not None]
