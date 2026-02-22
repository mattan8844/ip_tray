import time
import logging
from dataclasses import dataclass

import rumps

from .net import (
    get_flag_emoji_for_country,
    get_local_ip,
    get_network_speeds_tick,
    get_public_ip_and_country,
    get_traffic_totals,
    human_speed,
    human_traffic_gb,
)
from .config import (
    PUBLIC_REFRESH_OPTIONS,
    REQUEST_TIMEOUT_OPTIONS,
    UPDATE_INTERVAL_OPTIONS,
    load_runtime_config,
    save_runtime_config,
)


UPDATE_INTERVAL_SEC = 1.0
PUBLIC_IP_REFRESH_SEC = 30.0
REQUEST_TIMEOUT_SEC = 3.5


logger = logging.getLogger(__name__)


def _cycle_float(current: float, options: tuple[float, ...]) -> float:
    try:
        idx = options.index(current)
    except ValueError:
        return options[0]
    return options[(idx + 1) % len(options)]


@dataclass
class NetState:
    public_ip: str = "-"
    country_code: str = ""
    local_ip: str = "-"
    up_bps: float = 0.0
    down_bps: float = 0.0
    up_total: float = 0.0
    down_total: float = 0.0


class IPTrayApp(rumps.App):
    def __init__(self):
        super().__init__("IPTray", quit_button=None)

        self.state = NetState()
        self.config = load_runtime_config()
        self.last_public_refresh = 0.0
        self.notifications_enabled = self.config.notifications_enabled

        # Menu items
        self.menu_public_ip = rumps.MenuItem("Public IP: -")
        self.menu_local_ip = rumps.MenuItem("Local IP: -")
        self.menu_separator1 = rumps.separator
        self.menu_speed_down = rumps.MenuItem("Down: -")
        self.menu_speed_up = rumps.MenuItem("Up: -")
        self.menu_traffic = rumps.MenuItem("Traffic: -")
        self.menu_separator2 = rumps.separator
        self.menu_notifications = rumps.MenuItem("通知提醒", callback=self.toggle_notifications)
        self.menu_notifications.state = self.notifications_enabled
        self.menu_update_interval = rumps.MenuItem("刷新频率: 1.0s", callback=self.toggle_update_interval)
        self.menu_public_refresh = rumps.MenuItem("公网刷新: 30s", callback=self.toggle_public_refresh)
        self.menu_timeout = rumps.MenuItem("请求超时: 3.5s", callback=self.toggle_request_timeout)
        self.menu_status = rumps.MenuItem("状态: 正常")
        self.menu_separator3 = rumps.separator
        self.menu_quit = rumps.MenuItem("Quit ⏻", callback=self.on_quit)

        self.menu = [
            self.menu_public_ip,
            self.menu_local_ip,
            self.menu_separator1,
            self.menu_speed_down,
            self.menu_speed_up,
            self.menu_traffic,
            self.menu_separator2,
            self.menu_notifications,
            self.menu_update_interval,
            self.menu_public_refresh,
            self.menu_timeout,
            self.menu_status,
            self.menu_separator3,
            self.menu_quit,
        ]

        # Start periodic timer (GUI-safe)
        self._timer = rumps.Timer(self._tick, self.config.update_interval)
        self._timer.start()
        self._update_menu_items()

    def on_quit(self, _):
        rumps.quit_application()

    def _tick(self, _):
        try:
            now = time.time()
            # IPs (rate-limited public IP)
            if now - self.last_public_refresh >= self.config.public_refresh_interval or not self.state.public_ip:
                old_ip, old_cc = self.state.public_ip, self.state.country_code
                pub_ip, cc = get_public_ip_and_country(timeout=self.config.request_timeout)
                if pub_ip:
                    self.state.public_ip = pub_ip
                if cc:
                    self.state.country_code = cc
                self.last_public_refresh = now
                # Notify on changes
                if self.notifications_enabled and (self.state.public_ip != old_ip or self.state.country_code != old_cc):
                    flag = get_flag_emoji_for_country(self.state.country_code) if self.state.country_code else "🏳️"
                    rumps.notification(
                        title="Public IP Changed",
                        subtitle=f"{flag} {self.state.country_code or ''}",
                        message=self.state.public_ip or "-",
                        sound=True,
                    )

            self.state.local_ip = get_local_ip() or self.state.local_ip

            # Speeds and totals (non-blocking tick-based)
            down_bps, up_bps = get_network_speeds_tick()
            self.state.down_bps = down_bps
            self.state.up_bps = up_bps

            down_total, up_total = get_traffic_totals()
            self.state.down_total = down_total
            self.state.up_total = up_total

            # Update UI
            self._update_menu_title()
            self._update_menu_items()
            self.menu_status.title = "状态: 正常"
        except (OSError, ValueError) as exc:
            logger.warning("Tick failed with recoverable error: %s", exc)
            self.menu_status.title = "状态: 网络异常"
        except Exception:
            logger.exception("Unexpected error in tray tick")
            self.menu_status.title = "状态: 内部错误"

    def _update_menu_title(self):
        flag = get_flag_emoji_for_country(self.state.country_code) if self.state.country_code else "🏳️"
        # Try to keep it compact; show a short code with speeds
        d = human_speed(self.state.down_bps)
        u = human_speed(self.state.up_bps)
        self.title = f"{flag} ↓{d} ↑{u}"

    def _update_menu_items(self):
        self.menu_public_ip.title = f"Public IP: {self.state.public_ip or '-'}"
        self.menu_local_ip.title = f"Local IP: {self.state.local_ip or '-'}"
        self.menu_speed_down.title = f"Down: {human_speed(self.state.down_bps)}"
        self.menu_speed_up.title = f"Up: {human_speed(self.state.up_bps)}"
        total_str = f"↓{human_traffic_gb(self.state.down_total)}  ↑{human_traffic_gb(self.state.up_total)}"
        self.menu_traffic.title = f"Traffic: {total_str}"
        self.menu_update_interval.title = f"刷新频率: {self.config.update_interval:.1f}s"
        self.menu_public_refresh.title = f"公网刷新: {int(self.config.public_refresh_interval)}s"
        self.menu_timeout.title = f"请求超时: {self.config.request_timeout:.1f}s"


    def toggle_notifications(self, sender):
        # Toggle checkmark state and internal flag
        sender.state = not bool(sender.state)
        self.notifications_enabled = bool(sender.state)
        self.config.notifications_enabled = self.notifications_enabled
        self._persist_config()

    def toggle_update_interval(self, _):
        self.config.update_interval = _cycle_float(self.config.update_interval, UPDATE_INTERVAL_OPTIONS)
        self._timer.interval = self.config.update_interval
        self._update_menu_items()
        self._persist_config()

    def toggle_public_refresh(self, _):
        self.config.public_refresh_interval = _cycle_float(self.config.public_refresh_interval, PUBLIC_REFRESH_OPTIONS)
        self._update_menu_items()
        self._persist_config()

    def toggle_request_timeout(self, _):
        self.config.request_timeout = _cycle_float(self.config.request_timeout, REQUEST_TIMEOUT_OPTIONS)
        self._update_menu_items()
        self._persist_config()

    def _persist_config(self):
        save_runtime_config(self.config)

def run():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s [%(name)s] %(message)s")
    IPTrayApp().run()


if __name__ == "__main__":
    run()
