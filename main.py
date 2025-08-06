import requests
from datetime import datetime, timezone
from astral import LocationInfo
from astral.sun import zenith
import math
import platform
import ctypes
import ctypes.util
import time
# from shared.config import ConfigFileManager

def clamp(n, minimum, maximum):
    return max(minimum, min(maximum, n))

class LocationTimeHandler:
    location: LocationInfo

    def __init__(self):
        self.set_manual_location(0, 0)
    
    def set_manual_location(self, lat, lon):
        self.location = LocationInfo(latitude=lat, longitude=lon)
    
    def update_location(self):
        data = requests.get("https://ipinfo.io/json").json()
        lat, lon = map(float, data["loc"].split(","))

        self.set_manual_location(lat, lon)
    
    def get_sun_elevation_angle(self):
        time = datetime.now(timezone.utc)
        elevation_angle = 90 - zenith(self.location.observer, time, True)

        return elevation_angle
    
    def get_night_shift(self):
        elevation_angle = self.get_sun_elevation_angle()

        return 1 - 1 / (1 + math.exp(-(elevation_angle - 10) / 3))

class TemperatureHandler:
    day_temp: float
    night_temp: float
    dim_percent: float
    brightness_gamma: float

    def __init__(self):
        self.day_temp = 6500
        self.night_temp = 3000
        self.dim_percent = 0.3
        self.brightness_gamma = 2.2
    
    def get_temp_colour(self, night_shift):
        temperature = self.day_temp + (self.night_temp - self.day_temp) * night_shift
        temperature /= 100

        if temperature <= 66:
            red = 255
        else:
            red = 329.698727446 * ((temperature - 60) ** -0.1332047592)
            red = clamp(red, 0, 255)

        if temperature <= 66:
            green = 99.4708025861 * math.log(temperature) - 161.1195681661
        else:
            green = 288.1221695283 * ((temperature - 60) ** -0.0755148492)
            green = clamp(green, 0, 255)
        
        if temperature >= 66:
            blue = 255
        elif temperature <= 19:
            blue = 0
        else:
            blue = 138.5177312231 * math.log(temperature - 10) - 305.0447927307
            blue = clamp(blue, 0, 255)
        
        return (red / 255, green / 255, blue / 255)
    
    def get_temp_brightness(self, night_shift):
        return 1 - self.dim_percent * math.pow(night_shift, self.brightness_gamma)

class Display:
    platform: str

    xf86vm: ctypes.CDLL
    display: int
    screen: int
    c_int_size: int

    def __init__(self):
        self.platform = platform.system()

        if self.platform != "Linux":
            raise NotImplementedError(f"Unsupported OS: {self.platform}" "Supported platforms: Linux")
        
        x11_library = ctypes.util.find_library("X11")
        xf86vm_library = ctypes.util.find_library("Xxf86vm")

        if not x11_library:
            raise ImportError("X11 library not found.")
        
        if not xf86vm_library:
            raise ImportError("Xxf86vm library not found.")
        
        x11 = ctypes.cdll.LoadLibrary(x11_library)
        xf86vm = ctypes.cdll.LoadLibrary(xf86vm_library)

        x11.XOpenDisplay.restype = ctypes.c_void_p
        display = x11.XOpenDisplay(None)

        screen = x11.XDefaultScreen(display)

        size = ctypes.c_int()
        xf86vm.XF86VidModeGetGammaRampSize(display, screen, ctypes.byref(size))

        self.xf86vm = xf86vm
        self.display = display
        self.screen = screen
        self.c_int_size = size.value
    
    def set_display(self, colour: tuple[float, float, float], brightness: float):
        red_arr, green_arr, blue_arr = [(ctypes.c_ushort * self.c_int_size)() for _ in range(3)]

        for i in range(self.c_int_size):
            val = 65535 * (i / self.c_int_size) * brightness
            red_arr[i] = int(val * colour[0])
            green_arr[i] = int(val * colour[1])
            blue_arr[i] = int(val * colour[2])

        self.xf86vm.XF86VidModeSetGammaRamp(self.display, self.screen, self.c_int_size, red_arr, green_arr, blue_arr)

class App:
    night_handler: LocationTimeHandler
    temp_handler: TemperatureHandler
    display: Display

    def __init__(self):
        self.night_handler = LocationTimeHandler()
        self.temp_handler = TemperatureHandler()
        self.display = Display()

        self.night_handler.update_location()

    def start(self):
        while True:
            self.update()

            time.sleep(30)
    
    def update(self):
        night_shift = self.night_handler.get_night_shift()
        colour = self.temp_handler.get_temp_colour(night_shift)
        brightness = self.temp_handler.get_temp_brightness(night_shift)

        self.display.set_display(colour, brightness)

if __name__ == "__main__":
    app = App()
    app.start()