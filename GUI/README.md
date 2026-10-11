# Live Capture · Python / Tkinter GUI

[返回项目首页](../README.md) · [原生 App](README-native.md) · [故障排查](../docs/troubleshooting.md)

`app.py` 是单任务录制器，使用 Python 标准库创建界面、启动 FFmpeg、读取进度并发送进程信号。无需安装第三方 Python 包。

## 准备环境

需要 macOS、Python 3.11+、可用的 Tk 和 FFmpeg。Python 3.11 是本仓库声明的最低版本；FFmpeg 与 Tk 需要单独具备，`pip install .` 不会替你安装它们。

先检查已有环境：

```bash
python3 --version
python3 -m tkinter
ffmpeg -version
```

第二条命令应打开测试窗口，验证后关闭窗口。若提示 `No module named '_tkinter'`，这不是可以通过 `pip install tkinter` 解决的缺包问题，需要解释器对应的 Tk 支持。

### 使用配套的 Homebrew Python 与 Tk

以下固定使用 3.13 作为一组配套环境，避免 Python 与 Tk 版本混用：

```bash
brew install python@3.13 python-tk@3.13 ffmpeg
python3.13 --version
python3.13 -m tkinter
```

`python-tk@3.13` 只对应 Python 3.13。使用其他解释器时，按[故障排查](../docs/troubleshooting.md#python-tk)检查其安装路径，并安装匹配的 Tk。

## 启动

在仓库根目录执行：

```bash
python3 GUI/app.py
```

使用上面的 Homebrew 3.13 配套环境时，明确指定解释器：

```bash
python3.13 GUI/app.py
```

也可以双击 `GUI/launch.command`，或在终端执行：

```bash
./GUI/launch.command
```

启动脚本使用 PATH 中的 `python3`，不会自动选择 `python3.13`。若脚本启动失败，而 `python3.13 GUI/app.py` 正常，请继续使用明确指定解释器的命令。

## 完成一次录制

1. 填入完整直播流 URL，点击「选择…」选择保存目录。
2. 文件名前缀填 `demo`，最长录制时长填 `00:00:30`。
3. 勾选保持 Mac 唤醒，点击 **Start**。
4. 检查大小、时长和日志；等待任务退出，检查生成的 MKV。

最长时长留空不添加上限。输出文件格式为 `<前缀>_<YYYYMMDD_HHMMSS>.mkv`，默认目录为当前用户桌面；前缀不用填写扩展名。

## 控制与关闭

| 按钮 | 进程行为 |
| --- | --- |
| Start | 启动 FFmpeg；已有任务运行时不能启动另一条 |
| Pause | 对录制进程组发送 `SIGSTOP` |
| Resume | 对进程组发送 `SIGCONT` |
| Stop | 对进程组发送 `SIGTERM`，请求收尾 |
| Kill | 对进程组发送 `SIGKILL` |

**暂停时需要结束录制，先 Resume，再 Stop。** 暂停的是进程，不保证直播源会保存暂停期间的分片。

运行中关闭窗口，界面会询问是否先发送 Stop；选择否也会关闭窗口，且不会保存任务或提供下次接管入口。建议主动 Stop，等待日志显示进程退出后再关闭。收到停止信号后显示 `Exited` 不一定代表输出不可播放，需要检查实际文件。

勾选保持唤醒会用 `caffeinate -dimsu` 包裹 FFmpeg。界面显示的 PID 是启动进程的 PID，勾选时可能对应 `caffeinate`；信号发送给该进程组。附加到原生 App 时应使用 FFmpeg 自身的 PID。

## 源码入口

| 位置 | 职责 |
| --- | --- |
| `RecorderState` | 状态、PID、文件、大小、时长与速度 |
| `start_recording()` | 参数读取、文件命名、FFmpeg 命令与进程启动 |
| `_read_process_output()` | 后台线程读取输出并写入队列 |
| `_drain_log_queue()` | Tk 主线程处理进度、日志与退出消息 |
| `_send_signal()` | 对录制进程组发送控制信号 |
| `_on_close()` | 窗口关闭行为 |

当前版本没有自动重连、URL 刷新、任务持久化、自定义 HTTP Header 或多任务管理。改动后按[贡献指南](../CONTRIBUTING.md)验证实际进程行为。
