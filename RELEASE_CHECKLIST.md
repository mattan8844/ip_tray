# 发布前检查清单

## 1. 版本与元数据
- [ ] 更新 `pyproject.toml` 中 `version`
- [ ] 确认 `description`、`authors`、`requires-python` 信息准确
- [ ] 确认 `project.scripts` 入口仍为 `ip-tray = ip_tray.app:run`

## 2. 依赖与环境
- [ ] 在全新虚拟环境安装：`pip install -r requirements.txt && pip install -e .`
- [ ] 验证 macOS 上可正常启动菜单栏应用
- [ ] 检查是否存在未使用或冲突依赖

## 3. 质量门禁
- [ ] 运行单元测试：`python -m unittest discover -s tests -p "test_*.py"`
- [ ] 运行开发检查：`python scripts/dev_check.py --skip-network`
- [ ] GitHub Actions CI 绿色通过

## 4. 功能与体验回归
- [ ] 菜单显示：公网/内网 IP、上下行速度、累计流量、状态行
- [ ] 配置切换：刷新频率、公网刷新间隔、请求超时、通知开关
- [ ] 配置持久化：重启应用后配置保持不变
- [ ] 异常场景：断网/接口失败时状态可见且应用不中断

## 5. 文档与发布说明
- [ ] README 与实际行为一致（包含菜单配置与 `--skip-network`）
- [ ] 记录已知限制（仅 macOS、网络接口依赖）
- [ ] 确认打包方式（pyinstaller 或 py2app）与步骤
