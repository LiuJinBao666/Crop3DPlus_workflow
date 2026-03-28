import threading
import time
import tkinter as tk
from tkinter import ttk

try:
    import serial
    from serial import SerialException
except ImportError:
    serial = None
    SerialException = Exception


class TurntableControllerApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Turntable Serial Controller")
        self.root.geometry("640x640")
        self.root.minsize(560, 360)

        self.port = "COM3"
        self.baudrate = 9600
        self.serial_conn = None
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.connected = False

        self.status_var = tk.StringVar(value="Searching for COM3...")
        self.detail_var = tk.StringVar(value="Disconnected")
        self.port_var = tk.StringVar(value=self.port)
        self.baud_var = tk.StringVar(value=str(self.baudrate))

        self._build_style()
        self._build_ui()

        self.monitor_thread = threading.Thread(target=self.monitor_port, daemon=True)
        self.monitor_thread.start()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_style(self):
        self.root.configure(bg="#eef2f7")
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("Root.TFrame", background="#eef2f7")
        style.configure("Card.TFrame", background="#ffffff")
        style.configure("Title.TLabel", background="#eef2f7", foreground="#111827", font=("Segoe UI", 20, "bold"))
        style.configure("Subtitle.TLabel", background="#eef2f7", foreground="#4b5563", font=("Segoe UI", 10))
        style.configure("Section.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 11, "bold"))
        style.configure("Value.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 15))
        style.configure("Muted.TLabel", background="#ffffff", foreground="#6b7280", font=("Segoe UI", 10))
        style.configure("FieldName.TLabel", background="#ffffff", foreground="#6b7280", font=("Segoe UI", 10))
        style.configure("FieldValue.TLabel", background="#ffffff", foreground="#111827", font=("Segoe UI", 11, "bold"))
        style.configure("Go.TButton", font=("Segoe UI", 12, "bold"), padding=(18, 14), foreground="#ffffff", background="#16a34a")
        style.map(
            "Go.TButton",
            background=[("disabled", "#bbf7d0"), ("active", "#15803d"), ("pressed", "#166534")],
            foreground=[("disabled", "#f8fafc"), ("active", "#ffffff"), ("pressed", "#ffffff")],
        )
        style.configure("Stop.TButton", font=("Segoe UI", 12, "bold"), padding=(18, 14), foreground="#ffffff", background="#dc2626")
        style.map(
            "Stop.TButton",
            background=[("disabled", "#fecaca"), ("active", "#b91c1c"), ("pressed", "#991b1b")],
            foreground=[("disabled", "#f8fafc"), ("active", "#ffffff"), ("pressed", "#ffffff")],
        )

    def _build_ui(self):
        root_frame = ttk.Frame(self.root, style="Root.TFrame", padding=20)
        root_frame.pack(fill="both", expand=True)
        root_frame.columnconfigure(0, weight=1)

        ttk.Label(root_frame, text="Turntable Serial Controller", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            root_frame,
            text="Auto-detects COM3 and sends GO / ST commands after connection.",
            style="Subtitle.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        status_card = ttk.Frame(root_frame, style="Card.TFrame", padding=18)
        status_card.grid(row=2, column=0, sticky="ew")
        status_card.columnconfigure(0, weight=1)

        ttk.Label(status_card, text="Connection", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(status_card, textvariable=self.status_var, style="Value.TLabel").grid(
            row=1, column=0, sticky="w", pady=(10, 6)
        )
        ttk.Label(status_card, textvariable=self.detail_var, style="Muted.TLabel", wraplength=560).grid(
            row=2, column=0, sticky="w"
        )

        info_row = ttk.Frame(status_card, style="Card.TFrame")
        info_row.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        info_row.columnconfigure(0, weight=1)
        info_row.columnconfigure(1, weight=1)

        port_card = ttk.Frame(info_row, style="Card.TFrame", padding=12)
        port_card.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        ttk.Label(port_card, text="PORT", style="FieldName.TLabel").pack(anchor="w")
        ttk.Label(port_card, textvariable=self.port_var, style="FieldValue.TLabel").pack(anchor="w", pady=(4, 0))

        baud_card = ttk.Frame(info_row, style="Card.TFrame", padding=12)
        baud_card.grid(row=0, column=1, sticky="ew", padx=(8, 0))
        ttk.Label(baud_card, text="BAUD", style="FieldName.TLabel").pack(anchor="w")
        ttk.Label(baud_card, textvariable=self.baud_var, style="FieldValue.TLabel").pack(anchor="w", pady=(4, 0))

        action_card = ttk.Frame(root_frame, style="Card.TFrame", padding=18)
        action_card.grid(row=3, column=0, sticky="ew", pady=(16, 0))
        action_card.columnconfigure(0, weight=1)
        action_card.columnconfigure(1, weight=1)

        ttk.Label(action_card, text="Actions", style="Section.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 14)
        )

        self.go_btn = ttk.Button(action_card, text="Send GO", style="Go.TButton", command=self.send_go)
        self.go_btn.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        self.stop_btn = ttk.Button(action_card, text="Send ST", style="Stop.TButton", command=self.send_stop)
        self.stop_btn.grid(row=1, column=1, sticky="ew", padx=(10, 0))

        log_card = ttk.Frame(root_frame, style="Card.TFrame", padding=18)
        log_card.grid(row=4, column=0, sticky="nsew", pady=(16, 0))
        root_frame.rowconfigure(4, weight=1)
        log_card.columnconfigure(0, weight=1)
        log_card.rowconfigure(1, weight=1)

        ttk.Label(log_card, text="Activity", style="Section.TLabel").grid(row=0, column=0, sticky="w")
        self.log_text = tk.Text(
            log_card,
            height=8,
            relief="flat",
            borderwidth=0,
            background="#ffffff",
            foreground="#111827",
            font=("Consolas", 10),
            padx=2,
            pady=8,
        )
        self.log_text.grid(row=1, column=0, sticky="nsew", pady=(10, 0))
        self.log_text.configure(state="disabled")

        self.update_button_state(False)
        self.append_log("Application started.")

    def safe_after(self, callback, *args):
        if not self.root.winfo_exists():
            return
        try:
            self.root.after(0, callback, *args)
        except tk.TclError:
            pass

    def append_log(self, message: str):
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"[{timestamp}] {message}\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def update_button_state(self, enabled: bool):
        state = "normal" if enabled else "disabled"
        self.go_btn.config(state=state)
        self.stop_btn.config(state=state)

    def set_connected_ui(self):
        self.connected = True
        self.status_var.set(f"{self.port} connected")
        if self.detail_var.get() in {"Disconnected", "Searching for COM3...", "Params: 9600 / 8N1"}:
            self.detail_var.set(f"Params: {self.baudrate} / 8N1")
        self.update_button_state(True)

    def set_disconnected_ui(self, detail: str):
        self.connected = False
        self.status_var.set(f"Searching for {self.port}...")
        self.detail_var.set(detail)
        self.update_button_state(False)

    def close_serial_locked(self):
        if self.serial_conn is None:
            return
        try:
            if self.serial_conn.is_open:
                self.serial_conn.close()
        except Exception:
            pass
        self.serial_conn = None

    def monitor_port(self):
        while not self.stop_event.is_set():
            if serial is None:
                self.safe_after(self.set_disconnected_ui, "pyserial not installed. Run: pip install pyserial")
                self.safe_after(self.append_log, "pyserial not installed.")
                time.sleep(2)
                continue

            try:
                with self.lock:
                    need_reconnect = self.serial_conn is None or not self.serial_conn.is_open

                if need_reconnect:
                    conn = serial.Serial(
                        port=self.port,
                        baudrate=self.baudrate,
                        bytesize=serial.EIGHTBITS,
                        parity=serial.PARITY_NONE,
                        stopbits=serial.STOPBITS_ONE,
                        timeout=1,
                        write_timeout=1,
                    )
                    with self.lock:
                        if self.stop_event.is_set():
                            conn.close()
                            return
                        self.serial_conn = conn
                    self.safe_after(self.set_connected_ui)
                    self.safe_after(self.append_log, f"Connected to {self.port}.")
                elif not self.connected:
                    self.safe_after(self.set_connected_ui)

            except SerialException as exc:
                with self.lock:
                    self.close_serial_locked()
                self.safe_after(self.set_disconnected_ui, f"{self.port} unavailable or busy: {exc}")
            except Exception as exc:
                with self.lock:
                    self.close_serial_locked()
                self.safe_after(self.set_disconnected_ui, f"Serial error: {exc}")

            time.sleep(1)

    def send_command(self, command: str):
        with self.lock:
            if self.serial_conn is None or not self.serial_conn.is_open:
                self.safe_after(self.set_disconnected_ui, f"{self.port} not connected. Cannot send command.")
                self.safe_after(self.append_log, f"Command blocked: {command}")
                return
            try:
                self.serial_conn.write((command + "\r").encode("ascii"))
                self.serial_conn.flush()
                self.detail_var.set(f"Last command: {command}")
                self.safe_after(self.append_log, f"Command sent: {command}")
            except Exception as exc:
                self.close_serial_locked()
                self.safe_after(self.set_disconnected_ui, f"Send failed: {exc}")
                self.safe_after(self.append_log, f"Command failed: {command}")

    def send_go(self):
        self.send_command("GO\r")

    def send_stop(self):
        self.send_command("ST\r")

    def on_close(self):
        self.stop_event.set()
        with self.lock:
            self.close_serial_locked()
        self.monitor_thread.join(timeout=1.5)
        self.root.destroy()


def main():
    root = tk.Tk()
    TurntableControllerApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
