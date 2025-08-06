import os
from pathlib import Path
from platformdirs import user_config_path, user_runtime_dir
from tempfile import gettempdir
from dotenv import load_dotenv, set_key
from configparser import ConfigParser
import socket
import json
import threading
import struct

LOCAL_HOST = "127.0.0.1"
APP_NAME = "BlueDim"

PORT_PATH = Path(user_runtime_dir() or gettempdir()) / APP_NAME / "port.json"
SETTINGS_PATH = user_config_path(APP_NAME) / "settings.conf"

Settings = dict[str, dict[str, float | int | bool | str]]

class SettingsManager:
    parser: ConfigParser
    path: Path
    state: Settings

    def __init__(self, path, default_state):
        self.parser = ConfigParser()
        self.path = path
        self.state = default_state
    
    def load_config_file(self):
        if not self.path.parent.exists():
            self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.touch()

        self.parser.read(self.path)
    
    def save_config_file(self):
        with self.path.open("w") as f:
            self.parser.write(f)

    def load(self):
        self.load_config_file()

        for section, options in self.state.items():
            if not self.parser.has_section(section):
                self.parser.add_section(section)

            for option, default_value in options.items():
                if self.parser.has_option(section, option):
                    value = self.parser.get(section, option)

                    try:
                        self.state[section][option] = type(default_value)(value)
                    except (ValueError, TypeError):
                        pass

                self.parser.set(section, option, str(default_value))

        for section in self.parser.sections():
            if section not in self.state:
                self.parser.remove_section(section)

                continue

            for (option, _) in self.parser.items(section):
                if option not in self.state[section]:
                    self.parser.remove_option(section, option)

                    continue
        
        self.save_config_file()
    
    def apply_changes(self, changes: Settings):
        self.load_config_file()

        for section, options in changes.items():
            if not section in self.state:
                continue

            if not self.parser.has_section(section):
                self.parser.add_section(section)

            for option, value in options.items():
                if not option in self.state[section]:
                    continue

                if type(self.state[section][option]) != type(value):
                    continue

                self.state[section][option] = value
                self.parser.set(section, option, str(value))
        
        self.save_config_file()

def get_port() -> int | None:
    try:
        with PORT_PATH.open("r", encoding="utf-8") as f:
            port_info = json.load(f)

            return int(port_info.get("port"))
    
    except (json.JSONDecodeError, OSError, ValueError, TypeError):
        return None

def set_port(port: int):
    if not PORT_PATH.parent.exists():
        PORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    with PORT_PATH.open("w", encoding="utf-8") as f:
        json.dump({"port": port}, f)

class RequestHandler():
    connection: socket.socket

    def __init__(self, connection):
        self.connection = connection
    
    def send_request(self, data):
        try:
            json_data = json.dumps(data).encode()
            self.connection.sendall(struct.pack(">I", len(json_data)) + json_data)

            return True
        except (json.JSONDecodeError, ConnectionError, OSError) as e:
            print(f"Send error: {e}")

            return False
    
    def get_request(self):
        try:
            length_bytes = self.connection.recv(4)

            if not length_bytes:
                return None
            
            length = struct.unpack(">I", length_bytes)[0]

            json_data = b""

            while len(json_data < length):
                packet = self.connection.recv(length - len(json_data))

                if not packet:
                    return None
                
                json_data += packet
            
            request = json.loads(json_data.decode())

            return request
        except (json.JSONDecodeError, ConnectionError, OSError) as e:
            print(f"Receive error: {e}")

            return None
    
    def end(self):
        self.connection.close()

class DaemonStateConfig:
    settings: SettingsManager

    def __init__(self, default_state):
        self.settings = SettingsManager(SETTINGS_PATH, default_state)
        self.settings.load()

    def handle_request(self, conn: socket.socket):
        request_handler = RequestHandler(conn)
        request = request_handler.get_request()

        if request:
            action = request.get("action")

            if action == "read":
                request_handler.send_request({"status": "success", "state": self.settings.state})
            elif action == "write":
                self.settings.apply_changes(request.get("changes") or {})
                request_handler.send_request({"status": "success"})
            else:
                request_handler.send_request({"status": "error"})
        
        request_handler.end()
    
    def start(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.bind((LOCAL_HOST, 0))
            _, port = s.getsockname()

            set_port(port)

            s.listen()

            while True:
                conn, _ = s.accept()

                threading.Thread(target=self.handle_request, args=(conn, _), daemon=True).start()

class InterfaceStateConfig:
    state: Settings
    port: int

    def __init__(self):
        port = get_port()

        if not port:
            return
        
        self.port = port

    def send_request(self, action, **args):
        with socket.socket() as s:
            s.connect((LOCAL_HOST, self.port))

            request_handler = RequestHandler(s)
            request_handler.send_request({"action": action, **args})

            response = request_handler.get_request()

            return response