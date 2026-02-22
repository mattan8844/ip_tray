import socket
import time
import logging
from typing import Optional, Tuple

import psutil
import requests


logger = logging.getLogger(__name__)


PUBLIC_IP_URLS = [
    "https://api64.ipify.org?format=json",
    "https://api.ip.sb/ip",
    "https://ifconfig.me/ip",
]

GEO_URLS = [
    "https://ipapi.co/json/",
    "https://ipinfo.io/json",
]


def get_public_ip_and_country(timeout: float = 3.5) -> Tuple[str, str]:
    ip = ""
    # Try multiple IP sources
    for url in PUBLIC_IP_URLS:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            try:
                data = r.json()
                ip = data.get("ip", "")
            except ValueError:
                ip = (r.text or "").strip()
            if ip:
                break
        except requests.RequestException as exc:
            logger.debug("Failed to fetch public IP from %s: %s", url, exc)
            continue

    country = ""
    for url in GEO_URLS:
        try:
            r = requests.get(url, timeout=timeout)
            r.raise_for_status()
            data = r.json()
            country = data.get("country", "") or data.get("country_code", "")
            if country:
                break
        except (requests.RequestException, ValueError) as exc:
            logger.debug("Failed to fetch geo info from %s: %s", url, exc)
            continue

    country = (country or "").upper()[:2]
    return ip, country


def get_local_ip() -> Optional[str]:
    s: Optional[socket.socket] = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.2)
        # A trick to get primary outbound interface IP without sending data
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        return ip
    except OSError as exc:
        logger.debug("Failed to get local IP: %s", exc)
        return None
    finally:
        if s is not None:
            s.close()


_LAST_BYTES = None
_LAST_TS = None


def get_network_speeds(interval: float = 1.0) -> Tuple[float, float]:
    global _LAST_BYTES, _LAST_TS
    now = time.time()
    io = psutil.net_io_counters()
    sent = io.bytes_sent
    recv = io.bytes_recv

    if _LAST_BYTES is None:
        _LAST_BYTES = (sent, recv)
        _LAST_TS = now
        # Blocking variant measures over interval
        time.sleep(max(0.0, interval))
        io2 = psutil.net_io_counters()
        sent2 = io2.bytes_sent
        recv2 = io2.bytes_recv
        dt = max(1e-6, time.time() - now)
        up_bps = (sent2 - sent) / dt
        down_bps = (recv2 - recv) / dt
        # Update last for subsequent calls
        _LAST_TS = time.time()
        _LAST_BYTES = (sent2, recv2)
    else:
        dt = max(1e-6, now - (_LAST_TS or now))
        up_bps = (sent - _LAST_BYTES[0]) / dt
        down_bps = (recv - _LAST_BYTES[1]) / dt
        _LAST_TS = now
        _LAST_BYTES = (sent, recv)

    return float(down_bps), float(up_bps)


def get_traffic_totals() -> Tuple[float, float]:
    io = psutil.net_io_counters()
    return float(io.bytes_recv), float(io.bytes_sent)


def get_network_speeds_tick() -> Tuple[float, float]:
    """Non-blocking speed computation suitable for GUI timer callbacks.

    Returns (down_bps, up_bps) based on deltas since last call.
    The first call returns (0.0, 0.0) while initializing state.
    """
    global _LAST_BYTES, _LAST_TS
    now = time.time()
    io = psutil.net_io_counters()
    sent = io.bytes_sent
    recv = io.bytes_recv

    if _LAST_BYTES is None or _LAST_TS is None:
        _LAST_BYTES = (sent, recv)
        _LAST_TS = now
        return 0.0, 0.0

    dt = max(1e-6, now - _LAST_TS)
    up_bps = (sent - _LAST_BYTES[0]) / dt
    down_bps = (recv - _LAST_BYTES[1]) / dt
    _LAST_TS = now
    _LAST_BYTES = (sent, recv)
    return float(down_bps), float(up_bps)


def get_flag_emoji_for_country(cc: str) -> str:
    if not cc or len(cc) != 2:
        return "🏳️"
    cc = cc.upper()
    base = 127397
    return chr(ord(cc[0]) + base) + chr(ord(cc[1]) + base)


def _trim_int_str(n: float, width: int = 4) -> str:
    s = str(int(round(n)))
    if len(s) <= width:
        return s
    # If exceeds width, keep most significant digits with suffix
    # e.g., 12345 -> 12k (approx), 1234567 -> 1M
    if n >= 1_000_000:
        return f"{int(n/1_000_000)}M"
    if n >= 1_000:
        return f"{int(n/1_000)}k"
    return s[:width]


def human_speed(bps: float) -> str:
    # bps here is bytes per second
    if bps is None:
        return "-"
    KB = 1024.0
    MB = KB * 1024.0
    if bps >= MB:
        val = bps / MB
        return f"{_trim_int_str(val)}MB/s"
    if bps >= KB:
        val = bps / KB
        return f"{_trim_int_str(val)}KB/s"
    return f"{_trim_int_str(bps)}B/s"


def human_traffic_gb(bytes_val: float) -> str:
    if bytes_val is None:
        return "-"
    GB = 1024.0 * 1024.0 * 1024.0
    val = bytes_val / GB
    # Keep up to 3 significant digits overall, but show as up to 4 integer width
    if val >= 100:
        return f"{int(val)}GB"
    elif val >= 10:
        return f"{val:.1f}GB"
    else:
        return f"{val:.2f}GB"


def fixed_speed_token(bps: float) -> str:
    """Return fixed-width speed token for stable tray title width.

    Format is always 5 chars: 4-digit right-aligned value + unit letter.
    Units: B/K/M/G (bytes per second scales). Values are capped at 9999.
    """
    if bps is None or bps < 0:
        return "   0B"

    KB = 1024.0
    MB = KB * 1024.0
    GB = MB * 1024.0

    if bps >= GB:
        value = int(round(bps / GB))
        unit = "G"
    elif bps >= MB:
        value = int(round(bps / MB))
        unit = "M"
    elif bps >= KB:
        value = int(round(bps / KB))
        unit = "K"
    else:
        value = int(round(bps))
        unit = "B"

    value = min(value, 9999)
    return f"{value:>4}{unit}"
