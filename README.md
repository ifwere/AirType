# AirType

用手机在电脑上打字。AirType 在电脑上启动一个局域网 HTTP 服务并显示二维码，手机扫码后即可在网页里输入文字，内容会通过剪贴板粘贴到电脑当前光标所在的输入框。

## 功能

- 扫码连接：自动获取局域网 IP，生成二维码，手机扫码即用
- 一键上屏：文字复制到剪贴板并自动模拟 Cmd+V（Windows/Linux 为 Ctrl+V）
- 自动发送：输入法合成结束后自动发送（可关闭），手动打字有 1.5 秒防抖
- 历史记录：浏览器 localStorage 保存最近 10 条，点击可重发
- 无依赖客户端：手机端只是普通网页，无需安装 App
- 单文件 GUI：tkinter 界面，启动后自动运行服务，15 秒后自动隐藏窗口，点击 Dock 图标可重新唤出

## 环境要求

| 项目 | 要求 |
|------|------|
| 系统 | macOS（源码理论上兼容 Windows/Linux，但打包脚本只覆盖 macOS） |
| Python | 3.13（`build.sh` 中固定使用 `python3.13`） |
| 图形库 | tkinter（python.org 官方安装包自带） |

### macOS 权限

AirType 通过 PyAutoGUI 模拟键盘，首次运行需要在「系统设置 -> 隐私与安全性 -> 辅助功能」中允许 AirType（开发运行时为终端或 IDE），否则文字会进入剪贴板但不会粘贴。部分系统还需要授予「屏幕录制」权限。

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 生成图标（首次运行或修改图标设计后）
python src/generate_icon.py

# 直接运行源码
python src/remote_server.py
```

## 打包

```bash
./build.sh
```

产物位于 `dist/AirType.app`。脚本会重新生成图标、清理旧的 `build/` `dist/` 和 `AirType.spec`，再调用 PyInstaller 生成 .app。

## 使用

1. 启动 AirType，窗口会自动显示可用的局域网 IP、端口和二维码
2. 确认手机与电脑连在同一个 Wi-Fi 下
3. 手机扫码（或点击界面中的蓝色链接在电脑浏览器打开）
4. 在网页输入框里输入文字，点击「发送」或回车；开启「输入完成后自动发送」时，停止输入后会自动上屏

## HTTP 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/` | 返回移动端输入页面 |
| POST | `/type` | JSON `{"text": "..."}`，复制到剪贴板并模拟粘贴 |

## 项目结构

| 路径 | 说明 |
|------|------|
| `src/remote_server.py` | 主程序：Flask 服务、tkinter 界面、二维码生成 |
| `src/generate_icon.py` | 用 Pillow 绘制图标，macOS 下生成 `.icns` |
| `build.sh` | 本地 macOS 打包脚本 |
| `.github/workflows/build-release.yml` | CI：构建 arm64 / x86_64 安装包并发布 Release |
| `requirements.txt` | 直接依赖清单 |

## 发布流程

推送 `v*` 形式的 tag 后，GitHub Actions 会分别在 `macos-15`（arm64）与 `macos-15-intel`（x86_64）上打包，做 ad-hoc 签名，生成 `AirType-<tag>-<arch>.zip` 及其 SHA256，并自动创建 Release。也可以手动触发 workflow，此时产物只作为 artifact 保留。

下载的 app 未使用开发者证书签名，首次打开需右键选择「打开」，或执行：

```bash
xattr -d com.apple.quarantine /Applications/AirType.app
```

## 安全说明

当前版本没有鉴权：同一局域网内的任何设备只要访问到该地址就能向电脑发送文字。请在可信网络中使用，不要将服务暴露到公网。`remote_server.py` 中保留了已注释的 Token 校验逻辑，如需启用可参照代码中的 `CURRENT_TOKEN` 部分恢复。

## 常见问题

| 问题 | 排查方向 |
|------|----------|
| 手机打不开页面 | 确认同一 Wi-Fi；关闭路由器的 AP 隔离；检查 macOS 防火墙是否放行 |
| 二维码显示 127.0.0.1 | 电脑未联网或只有回环地址，切换为其他网卡 IP 或检查网络 |
| 提示端口被占用 | 界面中手动修改端口后重新启动 |
| 文字进了剪贴板但没粘贴 | 检查辅助功能权限；确认焦点在目标输入框上 |
| 启动后窗口消失 | 设计如此，点击 Dock 图标可重新显示 |
