from datetime import datetime, timezone
from astral import LocationInfo
from astral.sun import zenith
import requests
import platform
# import subprocess
import ctypes
import ctypes.util
import time
import math

def clamp(n, minimum, maximum):
    return max(minimum, min(maximum, n))

class LocationHandler:
    location: LocationInfo

    def __init__(self):
        self.set_manual_location(0, 0)
    
    def set_manual_location(self, lat, lon):
        self.location = LocationInfo(latitude=lat, longitude=lon)
    
    def update_location(self):
        data = requests.get("https://ipinfo.io/json").json()
        lat, lon = map(float, data["loc"].split(","))

        self.set_manual_location(lat, lon)

class TempHandler:
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

class NightDetector:
    def __init__(self):
        pass

    def get_sun_elevation_angle(self, location: LocationInfo):
        time = datetime.now(timezone.utc)
        elevation_angle = 90 - zenith(location.observer, time, True)

        return elevation_angle
    
    def get_night_shift(self, location: LocationInfo):
        elevation_angle = self.get_sun_elevation_angle(location)

        return 1 - 1 / (1 + math.exp(-(elevation_angle - 10) / 3))

class Display:
    platform: str

    xf86vm: ctypes.CDLL
    display: int
    screen: int
    c_int_size: int
    c_array_type: type[ctypes.Array[ctypes.c_ushort]]

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

        c_int_size = size.value
        c_array_type = ctypes.c_ushort * c_int_size

        self.xf86vm = xf86vm
        self.display = display
        self.screen = screen
        self.c_int_size = c_int_size
        self.c_array_type = c_array_type
    
    def set_display(self, colour: tuple[float, float, float], brightness: float):
        colour_arrs = []

        for i in range(3):
            val = [int(65535 * (j / self.c_int_size) * colour[i] * brightness) for j in range(self.c_int_size)]
            arr = self.c_array_type(*val)

            colour_arrs.append(arr)

        self.xf86vm.XF86VidModeSetGammaRamp(self.display, self.screen, self.c_int_size, colour_arrs[0], colour_arrs[1], colour_arrs[2])

class App:
    def __init__(self):
        display = Display()
        display.set_display((1, 1, 1), 1)

App()

# def update():
#     current_time = datetime.now(timezone.utc)
#     latitude, longitude = get_location()
#     elevation_angle = get_sun_elevation_angle(latitude, longitude, current_time)

#     night_shift = get_night_shift(elevation_angle)
#     temperature = get_temperature(night_shift)
#     rgbScale = get_rgb_from_temp(temperature)
#     brightness = get_brightness(night_shift)

#     print(rgbScale)

#     print(elevation_angle)

#     set_display_appearance(rgbScale, brightness)

# while True:
#     update()

#     time.sleep(60)