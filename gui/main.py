import threading
import time
import tkinter as tk
from tkinter import ttk
import json
import shutil
import subprocess
import sys
from pathlib import Path
import serial
import serial.tools.list_ports
import pyautogui
import pystray
from PIL import Image, ImageDraw

# Disattiva il fail-safe di PyAutoGUI per evitare blocchi improvvisi muovendo il mouse agli angoli
pyautogui.FAILSAFE = False

class EncoderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Encoderino Control Panel")
        self.root.geometry("400x350")
        self.root.resizable(False, False)

        self.serial_port = None
        self.is_running = False
        self.flash_running = False
        self.reconnect_after_flash = False
        self.tray_icon = None
        self.tray_thread = None
        if getattr(sys, "frozen", False):
            executable_root = Path(sys.executable).resolve().parent
            internal_root = executable_root / "_internal"
            self.project_root = (
                internal_root if internal_root.is_dir() else executable_root
            )
        else:
            self.project_root = Path(__file__).resolve().parent.parent

        # Variabili di stato GUI
        self.port_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Audio Master")
        self.status_var = tk.StringVar(value="Disconnesso")

        self.create_widgets()
        self.refresh_ports()
        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)

    def create_widgets(self):
        # Frame Connessione Seriale
        conn_frame = ttk.LabelFrame(self.root, text=" Connessione Seriale ", padding=10)
        conn_frame.pack(fill="x", padx=15, pady=10)

        ttk.Label(conn_frame, text="Porta:").pack(side="left", padx=5)

        self.port_combo = ttk.Combobox(conn_frame, textvariable=self.port_var, width=15, state="readonly")
        self.port_combo.pack(side="left", padx=5)

        refresh_btn = ttk.Button(conn_frame, text="🔄", width=3, command=self.refresh_ports)
        refresh_btn.pack(side="left", padx=2)

        self.connect_btn = ttk.Button(conn_frame, text="Connetti", command=self.toggle_connection)
        self.connect_btn.pack(side="left", padx=5)

        # Frame Selezione Modalità (Funzionalità dell'Encoder)
        mode_frame = ttk.LabelFrame(self.root, text=" Modalità di Funzionamento ", padding=10)
        mode_frame.pack(fill="both", expand=True, padx=15, pady=5)

        modes = [
            ("Audio Master (Volume Generale + Mute)", "Audio Master"),
            ("Zoom/Scroll (Pagine web o codice)", "Zoom/Scroll"),
            ("Cambio Desktop Virtuali (Ctrl + Win + Frecce)", "Virtual Desktops")
        ]

        for text, val in modes:
            rb = ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=val)
            rb.pack(anchor="w", pady=5)

        firmware_frame = ttk.LabelFrame(self.root, text=" Firmware ", padding=10)
        firmware_frame.pack(fill="both", expand=True, padx=15, pady=5)

        self.flash_btn = ttk.Button(
            firmware_frame,
            text="Compila e carica firmware",
            command=self.flash_firmware,
        )
        self.flash_btn.pack(anchor="w")

        self.firmware_log = tk.Text(firmware_frame, height=6, width=45, state="disabled")
        self.firmware_log.pack(fill="both", expand=True, pady=(8, 0))

        # Barra di Stato in basso
        status_frame = ttk.Frame(self.root, padding=5)
        status_frame.pack(fill="x", padx=15, pady=5)

        ttk.Label(status_frame, text="Stato: ").pack(side="left")
        status_label = ttk.Label(status_frame, textvariable=self.status_var, font=("Segoe UI", 9, "bold"))
        status_label.pack(side="left")

    def refresh_ports(self):
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.port_combo['values'] = ports
        if ports:
            self.port_combo.current(0)

    def create_tray_image(self):
        image = Image.new("RGB", (64, 64), "white")
        draw = ImageDraw.Draw(image)
        draw.ellipse((8, 8, 56, 56), fill="#2563eb")
        draw.ellipse((24, 24, 40, 40), fill="white")
        return image

    def minimize_to_tray(self):
        self.root.withdraw()
        if self.tray_icon is not None:
            return

        menu = pystray.Menu(
            pystray.MenuItem("Apri Encoderino", self.restore_from_tray, default=True),
            pystray.MenuItem("Esci", self.quit_application),
        )
        self.tray_icon = pystray.Icon(
            "encoderino",
            self.create_tray_image(),
            "Encoderino",
            menu,
        )
        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def restore_from_tray(self, icon=None, item=None):
        self.root.after(0, self._restore_from_tray)

    def _restore_from_tray(self):
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def quit_application(self, icon=None, item=None):
        self.root.after(0, self._quit_application)

    def _quit_application(self):
        self.is_running = False
        if self.serial_port and self.serial_port.is_open:
            self.serial_port.close()
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        self.root.destroy()

    def find_arduino_cli(self):
        candidates = [
            self.project_root / "tools" / "arduino-cli" / "arduino-cli.exe",
            Path(__file__).resolve().parent / "arduino-cli.exe",
            shutil.which("arduino-cli"),
            shutil.which("arduino-cli.exe"),
            self.project_root / "arduino-cli.exe",
            self.project_root / "tools" / "arduino-cli.exe",
        ]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(candidate)
        return None

    def append_firmware_log(self, message):
        self.firmware_log.config(state="normal")
        self.firmware_log.insert("end", message + "\n")
        self.firmware_log.see("end")
        self.firmware_log.config(state="disabled")

    def run_cli_command(self, command):
        process = subprocess.Popen(
            command,
            cwd=self.project_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
        output = []
        for line in process.stdout:
            line = line.rstrip()
            output.append(line)
            self.root.after(0, self.append_firmware_log, line)
        process.wait()
        return process.returncode, "\n".join(output)

    def install_arduino_dependencies(self, cli_path):
        self.root.after(0, self.append_firmware_log, "Verifica Arduino AVR core...")
        return_code, _ = self.run_cli_command(
            [cli_path, "core", "install", "arduino:avr"]
        )
        if return_code != 0:
            return False

        self.root.after(0, self.append_firmware_log, "Verifica libreria Encoder...")
        return_code, _ = self.run_cli_command(
            [cli_path, "lib", "install", "Encoder"]
        )
        return return_code == 0

    def detect_board_fqbn(self, cli_path, port):
        command = [cli_path, "board", "list", "--json"]
        return_code, output = self.run_cli_command(command)
        if return_code != 0:
            return None
        try:
            board_list = json.loads(output)
        except json.JSONDecodeError:
            return None

        for detected_port in board_list.get("detected_ports", []):
            port_info = detected_port.get("port", {})
            if port_info.get("address") != port:
                continue
            matching_boards = detected_port.get("matching_boards", [])
            if matching_boards:
                return matching_boards[0].get("fqbn")
        return None

    def flash_firmware(self):
        if self.flash_running:
            return
        port = self.port_var.get()
        if not port:
            self.append_firmware_log("Seleziona una porta seriale prima del flashing.")
            return

        cli_path = self.find_arduino_cli()
        if not cli_path:
            self.append_firmware_log(
                "arduino-cli non trovato. Inserisci il file in "
                "tools\\arduino-cli\\arduino-cli.exe o aggiungilo al PATH."
            )
            return

        self.flash_running = True
        self.reconnect_after_flash = self.is_running
        if self.is_running:
            self.toggle_connection()
            self.append_firmware_log("Connessione seriale sospesa durante il flashing.")
        self.flash_btn.config(state="disabled")
        self.append_firmware_log(f"Uso arduino-cli: {cli_path}")
        threading.Thread(
            target=self._flash_firmware_worker,
            args=(cli_path, port),
            daemon=True,
        ).start()

    def _flash_firmware_worker(self, cli_path, port):
        try:
            firmware_path = self.project_root / "firmware"
            if not self.install_arduino_dependencies(cli_path):
                self.root.after(0, self.append_firmware_log, "Impossibile preparare le dipendenze Arduino.")
                return

            fqbn = self.detect_board_fqbn(cli_path, port)
            if not fqbn:
                self.root.after(0, self.append_firmware_log, "Scheda non riconosciuta sulla porta selezionata.")
                return

            self.root.after(0, self.append_firmware_log, f"Scheda rilevata: {fqbn}")
            compile_command = [cli_path, "compile", "--fqbn", fqbn, str(firmware_path)]
            return_code, _ = self.run_cli_command(compile_command)
            if return_code != 0:
                self.root.after(0, self.append_firmware_log, "Compilazione fallita.")
                return

            upload_command = [cli_path, "upload", "--port", port, "--fqbn", fqbn, str(firmware_path)]
            return_code, _ = self.run_cli_command(upload_command)
            message = "Firmware caricato correttamente." if return_code == 0 else "Upload fallito."
            self.root.after(0, self.append_firmware_log, message)
        except (OSError, subprocess.SubprocessError) as error:
            self.root.after(0, self.append_firmware_log, f"Errore arduino-cli: {error}")
        finally:
            self.root.after(0, self._finish_flash)
            if self.reconnect_after_flash:
                self.root.after(500, self.toggle_connection)
                self.reconnect_after_flash = False

    def _finish_flash(self):
        self.flash_running = False
        self.flash_btn.config(state="normal")

    def toggle_connection(self):
        if not self.is_running:
            port = self.port_var.get()
            if not port:
                return
            try:
                self.serial_port = serial.Serial(port, 9600, timeout=1)
                self.is_running = True
                self.connect_btn.config(text="Disconnetti")
                self.status_var.set("Connesso a " + port)

                # Avvia il thread di ascolto della seriale
                self.thread = threading.Thread(target=self.read_serial, daemon=True)
                self.thread.start()
            except Exception as e:
                self.status_var.set("Errore di connessione")
        else:
            self.is_running = False
            if self.serial_port and self.serial_port.is_open:
                self.serial_port.close()
            self.connect_btn.config(text="Connetti")
            self.status_var.set("Disconnesso")

    def read_serial(self):
        while self.is_running:
            try:
                if self.serial_port and self.serial_port.in_waiting > 0:
                    line = self.serial_port.readline().decode('utf-8').strip()
                    if line:
                        self.handle_command(line)
            except (serial.SerialException, UnicodeDecodeError) as error:
                print(f"Errore nella lettura seriale: {error}")
                break
            time.sleep(0.01)

    def handle_command(self, cmd):
        current_mode = self.mode_var.get()
        print(f"Comando ricevuto: {cmd} [Modalità: {current_mode}]")

        # Gestione in base alla modalità selezionata nella GUI
        if current_mode == "Audio Master":
            if cmd == "ENC_RIGHT":
                pyautogui.press("volumeup")
            elif cmd == "ENC_LEFT":
                pyautogui.press("volumedown")
            elif cmd == "ENC_CLICK":
                pyautogui.press("playpause") # <-- MODIFICATO QUI: da volumemute a playpause
        elif current_mode == "Zoom/Scroll":
            if cmd == "ENC_RIGHT":
                pyautogui.scroll(-2) # Scroll giù (o zoom out)
            elif cmd == "ENC_LEFT":
                pyautogui.scroll(2)  # Scroll sù (o zoom in)
            elif cmd == "ENC_CLICK":
                pyautogui.hotkey('ctrl', '0') # Reset zoom

        elif current_mode == "Virtual Desktops":
            if cmd == "ENC_RIGHT":
                pyautogui.hotkey('ctrl', 'win', 'right') # Desktop successivo
            elif cmd == "ENC_LEFT":
                pyautogui.hotkey('ctrl', 'win', 'left')  # Desktop precedente
            elif cmd == "ENC_CLICK":
                pyautogui.hotkey('win', 'tab')           # Task View

if __name__ == "__main__":
    root = tk.Tk()
    app = EncoderApp(root)
    root.mainloop()
