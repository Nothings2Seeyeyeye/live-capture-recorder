import os
import queue
import shlex
import signal
import subprocess
import threading
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


@dataclass
class RecorderState:
    status: str = "Idle"
    pid: str = "-"
    output_path: str = "-"
    size_bytes: int = 0
    out_time: str = "00:00:00"
    speed: str = "-"


class FFmpegRecorderApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Live Capture Monitor")
        self.root.geometry("920x680")
        self.root.minsize(840, 620)

        self.process: subprocess.Popen | None = None
        self.reader_thread: threading.Thread | None = None
        self.log_queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self.state = RecorderState()

        self.url_var = tk.StringVar()
        self.output_dir_var = tk.StringVar(value=str(Path.home() / "Desktop"))
        self.file_prefix_var = tk.StringVar(value="live")
        self.duration_var = tk.StringVar(value="")
        self.keep_awake_var = tk.BooleanVar(value=True)

        self.status_var = tk.StringVar(value=self.state.status)
        self.pid_var = tk.StringVar(value=self.state.pid)
        self.file_var = tk.StringVar(value=self.state.output_path)
        self.size_var = tk.StringVar(value="0 B")
        self.time_var = tk.StringVar(value=self.state.out_time)
        self.speed_var = tk.StringVar(value=self.state.speed)
        self.progress_var = tk.StringVar(value="Waiting to start")

        self._build_ui()
        self.root.after(150, self._drain_log_queue)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(2, weight=1)

        form = ttk.Frame(self.root, padding=16)
        form.grid(row=0, column=0, sticky="nsew")
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="直播流 URL").grid(row=0, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self.url_var).grid(row=0, column=1, columnspan=3, sticky="ew", pady=(0, 8))

        ttk.Label(form, text="保存目录").grid(row=1, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self.output_dir_var).grid(row=1, column=1, columnspan=2, sticky="ew", pady=(0, 8))
        ttk.Button(form, text="选择...", command=self._choose_directory).grid(row=1, column=3, sticky="ew", padx=(8, 0), pady=(0, 8))

        ttk.Label(form, text="文件名前缀").grid(row=2, column=0, sticky="w", pady=(0, 8))
        ttk.Entry(form, textvariable=self.file_prefix_var, width=18).grid(row=2, column=1, sticky="w", pady=(0, 8))

        ttk.Label(form, text="最长录制时长").grid(row=2, column=2, sticky="w", padx=(16, 0), pady=(0, 8))
        ttk.Entry(form, textvariable=self.duration_var, width=18).grid(row=2, column=3, sticky="ew", padx=(8, 0), pady=(0, 8))
        ttk.Label(form, text="留空表示录到直播结束，例如 07:00:00").grid(row=3, column=1, columnspan=3, sticky="w", pady=(0, 8))

        ttk.Checkbutton(form, text="录制时保持 Mac 唤醒", variable=self.keep_awake_var).grid(row=4, column=1, sticky="w", pady=(0, 8))

        buttons = ttk.Frame(self.root, padding=(16, 0))
        buttons.grid(row=1, column=0, sticky="ew")
        for index in range(5):
            buttons.columnconfigure(index, weight=1)

        self.start_button = ttk.Button(buttons, text="Start", command=self.start_recording)
        self.pause_button = ttk.Button(buttons, text="Pause", command=self.pause_recording)
        self.resume_button = ttk.Button(buttons, text="Resume", command=self.resume_recording)
        self.stop_button = ttk.Button(buttons, text="Stop", command=self.stop_recording)
        self.kill_button = ttk.Button(buttons, text="Kill", command=self.kill_recording)

        self.start_button.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self.pause_button.grid(row=0, column=1, sticky="ew", padx=8)
        self.resume_button.grid(row=0, column=2, sticky="ew", padx=8)
        self.stop_button.grid(row=0, column=3, sticky="ew", padx=8)
        self.kill_button.grid(row=0, column=4, sticky="ew", padx=(8, 0))

        status_frame = ttk.LabelFrame(self.root, text="状态", padding=16)
        status_frame.grid(row=2, column=0, sticky="nsew", padx=16, pady=(12, 0))
        status_frame.columnconfigure(1, weight=1)
        status_frame.rowconfigure(6, weight=1)

        self._status_row(status_frame, 0, "当前状态", self.status_var)
        self._status_row(status_frame, 1, "进程 PID", self.pid_var)
        self._status_row(status_frame, 2, "当前文件", self.file_var)
        self._status_row(status_frame, 3, "已写入大小", self.size_var)
        self._status_row(status_frame, 4, "录制时长", self.time_var)
        self._status_row(status_frame, 5, "处理速度", self.speed_var)

        ttk.Label(status_frame, textvariable=self.progress_var).grid(row=6, column=0, columnspan=2, sticky="w", pady=(8, 8))

        self.log_text = tk.Text(status_frame, height=18, wrap="word")
        self.log_text.grid(row=7, column=0, columnspan=2, sticky="nsew")
        self.log_text.configure(state="disabled")

        scrollbar = ttk.Scrollbar(status_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.grid(row=7, column=2, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self._set_controls()

    def _status_row(self, parent: ttk.Frame, row: int, label: str, variable: tk.StringVar) -> None:
        ttk.Label(parent, text=label).grid(row=row, column=0, sticky="nw", pady=4)
        ttk.Label(parent, textvariable=variable, wraplength=620).grid(row=row, column=1, sticky="w", pady=4)

    def _choose_directory(self) -> None:
        directory = filedialog.askdirectory(initialdir=self.output_dir_var.get() or str(Path.home()))
        if directory:
            self.output_dir_var.set(directory)

    def start_recording(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Already Running", "当前已经有录制任务在运行。")
            return

        url = self.url_var.get().strip()
        output_dir = self.output_dir_var.get().strip()
        prefix = self.file_prefix_var.get().strip() or "live"
        duration = self.duration_var.get().strip()

        if not url:
            messagebox.showerror("Missing URL", "请先粘贴直播流 URL。")
            return
        if not output_dir:
            messagebox.showerror("Missing Directory", "请先选择保存目录。")
            return

        Path(output_dir).mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = str(Path(output_dir) / f"{prefix}_{timestamp}.mkv")

        command = []
        if self.keep_awake_var.get():
            command.extend(["caffeinate", "-dimsu"])
        command.extend(
            [
                "ffmpeg",
                "-nostdin",
                "-hide_banner",
                "-progress",
                "pipe:1",
                "-nostats",
                "-i",
                url,
                "-c",
                "copy",
            ]
        )
        if duration:
            command.extend(["-t", duration])
        command.append(output_path)

        try:
            self.process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                preexec_fn=os.setsid,
            )
        except FileNotFoundError as exc:
            messagebox.showerror("Command Not Found", f"启动失败：{exc}")
            return
        except Exception as exc:
            messagebox.showerror("Start Failed", str(exc))
            return

        self.state = RecorderState(status="Running", pid=str(self.process.pid), output_path=output_path)
        self._refresh_state()
        self._append_log("INFO", f"启动命令: {' '.join(shlex.quote(part) for part in command)}")
        self._append_log("INFO", f"保存路径: {output_path}")

        self.reader_thread = threading.Thread(target=self._read_process_output, daemon=True)
        self.reader_thread.start()
        self._set_controls()

    def pause_recording(self) -> None:
        if self._send_signal(signal.SIGSTOP, "Paused"):
            self._append_log("INFO", "已暂停录制。")

    def resume_recording(self) -> None:
        if self._send_signal(signal.SIGCONT, "Running"):
            self._append_log("INFO", "已恢复录制。")

    def stop_recording(self) -> None:
        if self._send_signal(signal.SIGTERM, "Stopping"):
            self._append_log("INFO", "已发送停止信号，等待 ffmpeg 收尾。")

    def kill_recording(self) -> None:
        if self._send_signal(signal.SIGKILL, "Killed"):
            self._append_log("WARN", "已强制结束录制。")

    def _send_signal(self, sig: signal.Signals, next_status: str) -> bool:
        if not self.process or self.process.poll() is not None:
            messagebox.showinfo("No Active Task", "当前没有正在运行的录制任务。")
            return False
        try:
            os.killpg(os.getpgid(self.process.pid), sig)
            self.state.status = next_status
            self._refresh_state()
            self._set_controls()
            return True
        except ProcessLookupError:
            self._append_log("WARN", "进程已经退出。")
            self._finalize_process()
            return False
        except Exception as exc:
            messagebox.showerror("Signal Failed", str(exc))
            return False

    def _read_process_output(self) -> None:
        assert self.process is not None
        assert self.process.stdout is not None
        for raw_line in self.process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                self.log_queue.put(("progress", f"{key}={value}"))
            else:
                self.log_queue.put(("log", line))

        return_code = self.process.wait()
        self.log_queue.put(("exit", str(return_code)))

    def _drain_log_queue(self) -> None:
        while True:
            try:
                kind, payload = self.log_queue.get_nowait()
            except queue.Empty:
                break

            if kind == "progress":
                self._handle_progress(payload)
            elif kind == "log":
                self._append_log("LOG", payload)
            elif kind == "exit":
                self._handle_exit(payload)

        self.root.after(150, self._drain_log_queue)

    def _handle_progress(self, payload: str) -> None:
        key, value = payload.split("=", 1)
        if key == "total_size":
            try:
                self.state.size_bytes = int(value)
                self.size_var.set(self._format_size(self.state.size_bytes))
            except ValueError:
                pass
        elif key == "out_time":
            self.state.out_time = value.split(".")[0]
            self.time_var.set(self.state.out_time)
        elif key == "speed":
            self.state.speed = value
            self.speed_var.set(value)
        elif key == "progress":
            if value == "continue":
                self.progress_var.set(f"正在录制: {self.time_var.get()} | {self.size_var.get()} | speed {self.speed_var.get()}")
            elif value == "end":
                self.progress_var.set("录制完成，ffmpeg 已退出。")

    def _handle_exit(self, code_str: str) -> None:
        code = int(code_str)
        if code == 0:
            self._append_log("INFO", "ffmpeg 正常退出。")
            if self.state.status not in {"Killed", "Stopped"}:
                self.state.status = "Finished"
        else:
            self._append_log("WARN", f"ffmpeg 已退出，返回码 {code}。")
            if self.state.status != "Killed":
                self.state.status = "Exited"
        self._finalize_process()

    def _finalize_process(self) -> None:
        self.process = None
        self.state.pid = "-"
        self.pid_var.set(self.state.pid)
        self._refresh_state()
        self._set_controls()

    def _set_controls(self) -> None:
        running = self.process is not None and self.process.poll() is None
        paused = self.state.status == "Paused"
        self.start_button.configure(state="disabled" if running else "normal")
        self.pause_button.configure(state="normal" if running and not paused else "disabled")
        self.resume_button.configure(state="normal" if running and paused else "disabled")
        self.stop_button.configure(state="normal" if running else "disabled")
        self.kill_button.configure(state="normal" if running else "disabled")

    def _refresh_state(self) -> None:
        self.status_var.set(self.state.status)
        self.pid_var.set(self.state.pid)
        self.file_var.set(self.state.output_path)

    def _append_log(self, level: str, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {level}  {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _format_size(self, size_bytes: int) -> str:
        units = ["B", "KB", "MB", "GB", "TB"]
        value = float(size_bytes)
        for unit in units:
            if value < 1024 or unit == units[-1]:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{size_bytes} B"

    def _on_close(self) -> None:
        if self.process and self.process.poll() is None:
            should_close = messagebox.askyesno("录制仍在运行", "录制任务还在运行。要先发送 Stop 再退出界面吗？")
            if should_close:
                self.stop_recording()
                self.root.after(300, self.root.destroy)
                return
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    FFmpegRecorderApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
