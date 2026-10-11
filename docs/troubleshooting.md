# Live Capture 故障排查

[返回中文首页](../README.md) · [English README](../README.en.md) · [Python 环境](../GUI/README.md)

先定位故障发生在哪一层：无法投屏获取 URL，检查抓流工具和局域网；有 URL 但无法录制，检查 FFmpeg、签名和输出目录；已录出文件但无法播放，检查音视频流和容器。

所有终端命令默认从仓库根目录执行。示例中的 `recording.mkv` 与占位 URL 需要替换成实际值。

<a id="macos-open"></a>
## 原生 App 无法打开

### 1. 核对芯片和系统

```bash
uname -m
sw_vers -productVersion
file "GUI/Live Capture.app/Contents/MacOS/LiveCapture"
```

仓库中的二进制应显示 `Mach-O 64-bit executable arm64`，要求 Apple Silicon 与 macOS 13+。在 Rosetta 终端中 `uname -m` 可能显示 `x86_64`，可再从「关于本机」检查芯片。Intel Mac 请使用 Python GUI。

### 2. 分清系统提示与程序错误

当前 App 为 ad hoc 签名，未通过 Apple 公证。若系统提示开发者无法验证，先确认下载自本仓库，再按 [Apple 官方说明](https://support.apple.com/en-us/102445)在「系统设置 → 隐私与安全性」中查看相应的打开选项。

若提示 App 损坏、包含恶意软件或不符合系统要求，请记录原文并重新核对下载文件。不要把所有启动错误都当作未公证问题，也不需要全局关闭 Gatekeeper。

## 打开后找不到保存目录

当前原生构建默认使用 `/Users/Shared/LiveCapture/recording`。这是系统共享目录，正式录制前请点击「选择…」，改为自己的个人录制目录。

确认目录可写、磁盘有空间，外接磁盘仍连接，并且系统没有拒绝 App 的文件夹访问。如果日志出现 `Permission denied` 或 `No space left on device`，先解决目录或空间问题，再重新录制。

<a id="ffmpeg-path"></a>
## 找不到 FFmpeg

### 终端中也找不到

```bash
command -v ffmpeg
ffmpeg -version
```

没有路径或版本信息时，已有 Homebrew 的用户可以执行：

```bash
brew install ffmpeg
```

若 `brew` 本身也找不到，按 [Homebrew 的安装后步骤](https://docs.brew.sh/Installation#post-installation-steps)完成 PATH 设置，重新打开终端再检查。

### 终端正常，原生 App 仍失败

当前原生构建使用固定的 `/opt/homebrew/bin/ffmpeg`。检查：

```bash
test -x /opt/homebrew/bin/ffmpeg && /opt/homebrew/bin/ffmpeg -version
```

Apple Silicon 上默认 Homebrew 路径对应此位置。自定义路径安装的 FFmpeg 不一定会被此构建识别；可以改用通过 PATH 查找 `ffmpeg` 的 Python GUI。仓库没有 Swift 源码，因此无法按现有源码修改原生路径。

<a id="python-tk"></a>
## Python 提示缺少 `_tkinter`

先确认你实际使用哪个 Python：

```bash
python3 --version
python3 -c 'import sys; print(sys.executable)'
python3 -m tkinter
```

出现 `No module named '_tkinter'` 表示当前解释器缺少 Tk 支持，不是 `app.py` 的第三方依赖未安装。`pip install tkinter` 和创建虚拟环境都不会给解释器补上 Tk。

可以安装一组配套的 Homebrew Python 与 Tk：

```bash
brew install python@3.13 python-tk@3.13
python3.13 -m tkinter
python3.13 GUI/app.py
```

测试窗口正常出现后关闭它，再运行 GUI。若坚持使用其他 Python 版本，安装与其主次版本相匹配的 Tk 支持；不要把 `python-tk@3.13` 与 `python3.14` 混用。[Homebrew 的配套公式说明](https://formulae.brew.sh/formula/python-tk@3.13)与 [Python 的 Tkinter 文档](https://docs.python.org/3/library/tkinter.html)提供环境检查依据。

`launch.command` 使用 PATH 中的 `python3`。明确指定 `python3.13 GUI/app.py` 正常，而脚本失败时，说明两者可能选中了不同的解释器。

<a id="cast-device"></a>
## 手机投屏列表找不到设备

1. 确认抓流工具仍在运行，终端已经打印设备宣告信息，而不是启动错误。
2. 手机与 Mac 接入同一局域网；同名 Wi-Fi 仍可能配置了访客隔离或 AP 隔离。
3. 如果正在使用 VPN、多网卡或企业网络，检查路由和局域网发现是否受影响；可先在普通家庭网络复现。
4. 核对防火墙和当前系统的本地网络访问设置，确认抓流进程可以进行所需的设备发现。
5. 只启用 DLNA，再刷新发送端的投屏列表：

```bash
uv tool run wechat-finder-dlna --protocol dlna --name "Live Capture"
```

若工具报端口占用，先确认是否已经有一个抓流实例运行。不要反复开启多个相同实例。

这一步属于第三方工具的设备发现；Live Capture 录制 App 不会出现在投屏列表里。已发现设备但没有输出可录制 URL 时，查看[抓流工具的上游文档](https://github.com/gtoxlili/wechat-finder-dlna)，确认发送端是否提供了支持的流地址。

<a id="stalled"></a>
## 文件不增长、FFmpeg 退出、HTTP 403 / 404

先看卡片的大小、时长和日志，不要只看 PID 是否存在。文件暂时不增长也可能是源流没有新分片，不能单凭一次刷新认定失败。

- **URL 被截断**：重新复制完整 URL，包含全部查询参数；GUI 中不需要额外加引号。
- **HTTP 403 / 签名失效**：重新投屏取得新 URL，再创建任务。当前版本不会刷新签名或补录间隙。
- **HTTP 404 / 直播结束**：确认直播仍在进行，并确认使用的是流地址而不是观看页面。
- **连接超时 / 网络断开**：检查网络与源站，再用新任务短录确认恢复。
- **任务仍在运行却不写入**：检查是否处于 Paused、磁盘是否已满、目录是否失去写权限，然后查看 FFmpeg 日志。

需要隔离 GUI 与 URL 问题时，可以在终端做一段 10 秒试录：

```bash
STREAM_URL='https://example.com/live/index.m3u8?replace=with-real-url'
ffmpeg -n -nostdin -hide_banner -i "$STREAM_URL" \
  -t 00:00:10 -c copy "diagnostic.mkv"
```

此 URL 是占位示例。若终端同样失败，优先处理源流、网络、编码或访问条件；GUI 没有 Cookie / Header 配置，不会自动补充登录信息。`-n` 避免覆盖已有诊断文件，重复试录时更换文件名。

<a id="paused-stop"></a>
## 暂停后 Stop 没反应

Pause 使用 `SIGSTOP` 暂停进程，暂停中的进程不能立即处理常规结束信号。先点击 **Resume**，再点击 **Stop**，等待日志显示退出。

Resume 后仍无法正常退出时，可以使用 Kill，但它不会让 FFmpeg 完成正常收尾。暂停过久还可能超过 HLS 分片窗口，恢复时不保证内容连续；需要完整保存一场直播时，尽量持续录制。

<a id="media-output"></a>
## 文件无法播放、没有声音或画面异常

### 1. 先检查文件包含什么流

```bash
ffprobe -v error -show_entries format=duration,size \
  -show_entries stream=codec_type,codec_name \
  -of json "recording.mkv"
```

检查是否出现 `codec_type: video` 和 `codec_type: audio`。源流没有音频时，转换文件不会生成缺失的声音。播放器不支持 MKV 或源编码时，先换用支持该格式的播放器。

### 2. 尝试重新封装

录制结束后，将实际文件路径替换到命令中：

```bash
ffmpeg -n -i "recording.mkv" -c copy -movflags +faststart "recording.mp4"
```

这条命令不重新编码。若报编码不适合 MP4，或目标播放器无法解码，可以尝试下面的 H.264 / AAC 转码，耗时和资源占用会增加：

```bash
ffmpeg -n -i "recording.mkv" -c:v libx264 -preset medium \
  -crf 20 -c:a aac -b:a 192k -movflags +faststart "recording-compatible.mp4"
```

需要 FFmpeg 构建包含 `libx264`。转码不能恢复没有录到的分片，也不能保证修复已损坏的输入。

<a id="timeline"></a>
## 日志提示自动修复时间轴失败

原生版会尝试录后处理。日志出现修复失败时，先保留输出并用 FFprobe / 播放器检查；失败消息不等于文件已损坏。

如果媒体可读取但时间轴或容器索引异常，可以在任务结束后另存一份重新封装的 MKV：

```bash
ffmpeg -n -fflags +genpts -i "recording.mkv" \
  -c copy -avoid_negative_ts make_zero "recording-remuxed.mkv"
```

检查新文件是否正常，再决定后续处理。这是排查尝试，不保证修复所有非单调时间戳或输入损坏。不要覆盖唯一的原始录制文件。

## 关闭 App、合盖或重启后发生什么

- 原生版保存任务信息，重开时尝试接管仍存活的进程。系统重启后原 PID 不再代表原录制，任务不会自动重新开始。
- Python 版运行中关闭会询问是否先 Stop。它没有持久化或重新附加入口，建议先 Stop 并确认退出。
- `caffeinate` 不能保证合盖、断电或所有系统睡眠情形下保持录制。长时间任务建议接电、保持网络稳定，并实际观察文件增长。

## 如何提交有用的问题报告

提供运行方式、芯片、macOS / Python / FFmpeg 版本、复现步骤、预期结果、实际结果和相关日志。可以从[问题模板](https://github.com/Nothings2Seeyeyeye/live-capture-recorder/issues/new/choose)开始。

发布日志或截图前，请去除直播 URL 的签名参数、Cookie、访问令牌和私人文件路径。现有 GUI 会将完整启动命令写入日志，因此日志可能包含完整流地址；分享时用 `https://example.com/live.m3u8?[REDACTED]` 替换，不要直接上传录制内容。
