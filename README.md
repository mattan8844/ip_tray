# IP Tray (macOS)

一个 macOS 菜单栏小工具，使用 Python + rumps 实现：
- 托盘标题显示当前外网 IP 所在国家的国旗 emoji，以及实时上下行网速（KB/s 或 MB/s，最多 4 位整数）。
- 菜单内展示：外网 IP、内网 IP、实时上下行速度、上下行累计流量（GB）、退出按钮。
- 每秒刷新速度统计；外网 IP + 地理信息默认每 30 秒刷新一次。

## 运行

建议使用 Python 3.9+。首先安装依赖：

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

开发调试（可选，快速校验非 GUI 功能）：

```bash
python scripts/dev_check.py
```

离线模式（用于 CI 或无外网环境）：

```bash
python scripts/dev_check.py --skip-network
```

启动菜单栏应用：

```bash
python -m ip_tray.app
```

或通过项目脚本（如已安装到环境）：

```bash
ip-tray
```

首次运行后，一个带有国旗与速度的图标会出现在菜单栏（屏幕右上角）。点击可展开菜单。

## 打包（可选）

可以使用 pyinstaller 或 py2app 打包为独立应用：
- pyinstaller（推荐简单）：
  - 安装：`pip install pyinstaller`
  - 构建：`pyinstaller --windowed --name "IP Tray" --paths src --hidden-import rumps src/ip_tray/app.py`
- py2app：
  - 安装：`pip install py2app`
  - 参考 py2app 文档创建 setup 配置后构建。

注意：首次运行可能需要“辅助功能/自动化”权限以在菜单栏显示；如果图标未出现，检查是否阻止了无窗口应用。

## 配置

运行时可在菜单中点击切换：
- 刷新频率（`0.5s / 1.0s / 2.0s / 5.0s`）
- 公网刷新间隔（`15s / 30s / 60s / 120s`）
- 请求超时（`2.0s / 3.5s / 5.0s / 8.0s`）
- 通知开关（公网 IP 或国家变化时提醒）

上述配置会自动保存到：`~/Library/Application Support/IPTray/config.json`。

## 发布

发布前请按清单逐项核对：`RELEASE_CHECKLIST.md`。
版本变更记录见：`CHANGELOG.md`。
执行命令参考：`RELEASE_COMMANDS.md`。

## 许可

MIT