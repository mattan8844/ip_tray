import time
import logging
import threading
from dataclasses import dataclass
from collections import deque
from pathlib import Path
import tempfile

import rumps
import objc
from Foundation import NSRunLoop, NSRunLoopCommonModes, NSObject

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
from .menu_graph_image import render_single_history_graph


HISTORY_SECONDS = 300
GRAPH_IMAGE_WIDTH = 180
GRAPH_IMAGE_HEIGHT = 32


logger = logging.getLogger(__name__)


class TrayMenuDelegate(NSObject):
    def initWithApp_(self, app):
        self = objc.super(TrayMenuDelegate, self).init()
        if self is None:
            return None
        self.app = app
        return self

    def menuWillOpen_(self, _):
        self.app.request_manual_public_refresh()


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
        self.up_history: deque[float] = deque(maxlen=HISTORY_SECONDS)
        self.down_history: deque[float] = deque(maxlen=HISTORY_SECONDS)
        self._graph_phase = False
        self._manual_refresh_lock = threading.Lock()
        self._manual_refresh_inflight = False
        self._manual_refresh_result: tuple[str, str, float] | None = None

        # Menu items
        self.menu_public_ip = rumps.MenuItem("Public IP: -")
        self.menu_local_ip = rumps.MenuItem("Local IP: -")
        self.menu_separator1 = rumps.separator
        self.menu_recv_rate = rumps.MenuItem("接收速率: -")
        self.menu_recv_graph = rumps.MenuItem("")
        self.menu_send_rate = rumps.MenuItem("发送速率: -")
        self.menu_send_graph = rumps.MenuItem("")
        self.menu_traffic = rumps.MenuItem("Traffic: -")
        self.menu_separator2 = rumps.separator
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
            self.menu_recv_rate,
            self.menu_recv_graph,
            self.menu_send_rate,
            self.menu_send_graph,
            self.menu_traffic,
            self.menu_separator2,
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
        if getattr(self._timer, "_nstimer", None) is not None:
            NSRunLoop.currentRunLoop().addTimer_forMode_(self._timer._nstimer, NSRunLoopCommonModes)
        self._menu_delegate = TrayMenuDelegate.alloc().initWithApp_(self)
        self._menu._menu.setDelegate_(self._menu_delegate)
        self._update_menu_items()
        self._update_menu_graph_images()
        self._update_tray_flag()

    def on_quit(self, _):
        rumps.quit_application()

    def _tick(self, _):
        try:
            self._apply_manual_public_refresh_result()
            now = time.time()
            # IPs (rate-limited public IP)
            if now - self.last_public_refresh >= self.config.public_refresh_interval or not self.state.public_ip:
                pub_ip, cc = get_public_ip_and_country(timeout=self.config.request_timeout)
                if pub_ip:
                    self.state.public_ip = pub_ip
                if cc:
                    self.state.country_code = cc
                self.last_public_refresh = now

            self.state.local_ip = get_local_ip() or self.state.local_ip

            # Speeds and totals (non-blocking tick-based)
            down_bps, up_bps = get_network_speeds_tick()
            self.state.down_bps = down_bps
            self.state.up_bps = up_bps
            self.down_history.append(down_bps)
            self.up_history.append(up_bps)

            down_total, up_total = get_traffic_totals()
            self.state.down_total = down_total
            self.state.up_total = up_total

            # Update UI
            self._update_tray_flag()
            self._update_menu_items()
            self._update_menu_graph_images()
            self.menu_status.title = "状态: 正常"
        except (OSError, ValueError) as exc:
            logger.warning("Tick failed with recoverable error: %s", exc)
            self.menu_status.title = "状态: 网络异常"
        except Exception:
            logger.exception("Unexpected error in tray tick")
            self.menu_status.title = "状态: 内部错误"

    def request_manual_public_refresh(self):
        with self._manual_refresh_lock:
            if self._manual_refresh_inflight:
                return
            self._manual_refresh_inflight = True
        self.menu_status.title = "状态: 手动刷新中"
        thread = threading.Thread(target=self._manual_public_refresh_worker, daemon=True)
        thread.start()

    def _manual_public_refresh_worker(self):
        try:
            pub_ip, cc = get_public_ip_and_country(timeout=self.config.request_timeout)
            with self._manual_refresh_lock:
                self._manual_refresh_result = (pub_ip, cc, time.time())
        except Exception:
            logger.exception("Manual public refresh failed")
        finally:
            with self._manual_refresh_lock:
                self._manual_refresh_inflight = False

    def _apply_manual_public_refresh_result(self):
        with self._manual_refresh_lock:
            result = self._manual_refresh_result
            self._manual_refresh_result = None

        if not result:
            return

        pub_ip, cc, refreshed_at = result
        if pub_ip:
            self.state.public_ip = pub_ip
        if cc:
            self.state.country_code = cc
        self.last_public_refresh = refreshed_at

        self._update_tray_flag()
        self._update_menu_items()
        self.menu_status.title = "状态: 正常"

    def _update_tray_flag(self):
        self.title = get_flag_emoji_for_country(self.state.country_code) if self.state.country_code else "🏳️"

    def _update_menu_items(self):
        self.menu_public_ip.title = f"Public IP: {self.state.public_ip or '-'}"
        self.menu_local_ip.title = f"Local IP: {self.state.local_ip or '-'}"
        self.menu_recv_rate.title = f"接收速率: {human_speed(self.state.down_bps)}"
        self.menu_send_rate.title = f"发送速率: {human_speed(self.state.up_bps)}"
        total_str = f"↓{human_traffic_gb(self.state.down_total)}  ↑{human_traffic_gb(self.state.up_total)}"
        self.menu_traffic.title = f"Traffic: {total_str}"
        self.menu_update_interval.title = f"刷新频率: {self.config.update_interval:.1f}s"
        self.menu_public_refresh.title = f"公网刷新: {int(self.config.public_refresh_interval)}s"
        self.menu_timeout.title = f"请求超时: {self.config.request_timeout:.1f}s"

    def _update_menu_graph_images(self):
        phase = "a" if self._graph_phase else "b"
        self._graph_phase = not self._graph_phase
        recv_path = Path(tempfile.gettempdir()) / "ip_tray" / f"menu_recv_{phase}.png"
        send_path = Path(tempfile.gettempdir()) / "ip_tray" / f"menu_send_{phase}.png"

        render_single_history_graph(
            samples=self.down_history,
            path=recv_path,
            line_color=(51, 123, 214, 255),
            fill_color=(74, 144, 226, 70),
            width=GRAPH_IMAGE_WIDTH,
            height=GRAPH_IMAGE_HEIGHT,
        )
        render_single_history_graph(
            samples=self.up_history,
            path=send_path,
            line_color=(232, 143, 25, 255),
            fill_color=(245, 166, 35, 70),
            width=GRAPH_IMAGE_WIDTH,
            height=GRAPH_IMAGE_HEIGHT,
        )

        self.menu_recv_graph.set_icon(str(recv_path), dimensions=(GRAPH_IMAGE_WIDTH, GRAPH_IMAGE_HEIGHT), template=False)
        self.menu_send_graph.set_icon(str(send_path), dimensions=(GRAPH_IMAGE_WIDTH, GRAPH_IMAGE_HEIGHT), template=False)


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
