# 发布命令清单

本清单默认你已经在项目根目录，并且已完成 `RELEASE_CHECKLIST.md` 的功能验收。

## A. GitHub Release（推荐）

### 1) 本地预检

```bash
source .venv/bin/activate
python -m unittest discover -s tests -p "test_*.py"
python scripts/dev_check.py --skip-network
```

### 2) 提交并打标签

```bash
git add .
git commit -m "release: v0.3.0"
git tag -a v0.3.0 -m "Release v0.3.0"
git push origin main
git push origin v0.3.0
```

### 3) 生成构建产物（可选）

```bash
source .venv/bin/activate
pip install pyinstaller
python -m PyInstaller --noconfirm "IP Tray.spec"
```

构建产物通常位于：
- `dist/IP Tray.app`（macOS 应用）

### 4) 创建 GitHub Release

在 GitHub 仓库页面：
1. 选择 tag：`v0.2.0`
2. 标题：`v0.2.0`
3. 描述可直接复制 `CHANGELOG.md` 的 0.3.0 小节
4. 如有产物，上传 `dist` 中的文件作为附件

---

## B. PyPI 发布（可选）

如果你也想把 Python 包发布到 PyPI，可执行以下流程。

### 1) 安装构建与上传工具

```bash
source .venv/bin/activate
pip install --upgrade build twine
```

### 2) 构建分发包

```bash
python -m build
```

生成文件位于 `dist/`（`.whl` 与 `.tar.gz`）。

### 3) 上传到 TestPyPI（建议先跑一遍）

```bash
python -m twine upload --repository testpypi dist/*
```

### 4) 上传到正式 PyPI

```bash
python -m twine upload dist/*
```

---

## C. 发版后验证

```bash
source .venv/bin/activate
pip install -e .
ip-tray
```

检查点：
- 菜单能正常显示和刷新
- 配置切换后重启仍保留
- 断网时状态提示正确
