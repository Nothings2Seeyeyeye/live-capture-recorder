# Live Capture · 原生 macOS App

[返回项目首页](../README.md) · [故障排查](../docs/troubleshooting.md)

原生版使用 SwiftUI 界面管理本机 FFmpeg，适合同时录制多场直播。当前仓库提供的是预编译 App。

## 运行条件

- Apple Silicon Mac，macOS 13 或更新版本。
- FFmpeg：当前构建使用 `/opt/homebrew/bin/ffmpeg`，对应 Apple Silicon 的默认 Homebrew 路径。
- 可写的输出目录和足够的磁盘空间。

原生 App 不依赖 Python，不包含 FFmpeg，也未经 Apple 公证。系统阻止打开时，先核对下载来源与错误提示，参考[对应排查步骤](../docs/troubleshooting.md#macos-open)。

## 启动

在仓库根目录执行：

```bash
brew install ffmpeg
test -x /opt/homebrew/bin/ffmpeg && /opt/homebrew/bin/ffmpeg -version
open "GUI/Live Capture.app"
```

也可在 Finder 中双击 `Live Capture.app`。所有主 README 中的终端命令均以仓库根目录为工作目录，除非明确写出其他路径。

## 第一条任务

1. 粘贴完整直播流 URL，保留签名查询参数。
2. 点击「选择…」，选择自己的个人保存目录。默认目录为 `/Users/Shared/LiveCapture/recording`，位于系统共享目录，正式录制前请主动更改。
3. 文件名前缀填 `demo`，最长时长填 `00:00:30`。
4. 点击 **Add Recording**，观察大小与媒体时长增长。
5. 完成后打开生成的 MKV，检查画面和声音。

最长时长留空不添加 `-t` 限制，填 `01:00:00` 则限制为约一小时输出媒体。每条录制独立生成带日期时间的文件，可重复添加多条任务。

## 管理任务

| 操作 | 行为 |
| --- | --- |
| Refresh | 更新任务的进程和文件信息 |
| Pause / Resume | 暂停 / 恢复录制进程；暂停期间的内容不保证可补录 |
| Stop | 请求 FFmpeg 结束并收尾；暂停时先 Resume |
| Kill | 强制结束无法正常退出的进程 |
| Attach by PID | 附加到自己已在运行的 FFmpeg 录制进程 |
| 清理已结束任务 | 整理已结束任务的卡片信息 |

任务卡片包含 PID、输出路径、文件大小、媒体时长、速度、日志和刷新时间。不要仅凭 Running 判断成功，应确认文件和时长确实增长。

原生版保存任务信息，重开时尝试重新接管仍存活的进程。系统重启后原有进程已消失，不会自动重建录制；附加任务的进度与日志可能比 App 内启动的任务少。

当前构建会尝试录后时间轴处理；若提示自动修复失败，保留输出文件，参考[时间轴排查](../docs/troubleshooting.md#timeline)重新封装。

## 构建状态

仓库中没有 Swift 源码、Xcode 工程、`Package.swift` 或 `build_app.sh`。因此当前不存在可执行的源码构建命令。

现有 App 的信息：

| 项目 | 当前值 |
| --- | --- |
| CPU 架构 | `arm64` |
| 最低 macOS | `13.0` |
| Bundle identifier | `org.livecapture.recorder` |
| Bundle version | `1.0` / build `1` |
| 签名 | ad hoc，无 Developer ID / Apple 公证 |

App 的 Bundle 版本与根目录 Python 项目元信息中的版本是两个独立字段，不代表已有同名 GitHub Release。

当前预编译交付已替换个人目录常量、使用通用 Bundle ID、更新构建 UUID，并重新进行 ad hoc 签名。这是对现有构建的隐私修订，不是从 Swift 源码重新编译；录制与进程管理逻辑保留。

需要修改可审查的录制源码时，请使用 [Python GUI](README.md)。贡献者不应声称能够从当前仓库重建原生 App，也不应直接提交来源不明的替换二进制。
