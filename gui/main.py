import threading
import time
import tkinter as tk
from tkinter import ttk
import serial
import serial.tools.list_ports
import pyautogui

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

        # Variabili di stato GUI
        self.port_var = tk.StringVar()
        self.mode_var = tk.StringVar(value="Audio Master")
        self.status_var = tk.StringVar(value="Disconnesso")

        self.create_widgets()
        self.refresh_ports()

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
            except Exception:
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
