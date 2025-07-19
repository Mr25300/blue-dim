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

NEUTRAL_TEMP = 6500
SHIFT_START_ANGLE = 15
SHIFT_END_ANGLE = -5

day_temp = 6500 # natural white light
night_temp = 3000 # orange colour
night_dim_percent = 0.4

def clamp(n, minimum, maximum):
    return max(minimum, min(maximum, n))

def get_rgb_from_temp(temperature):
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

def get_sun_elevation_angle(lat, lon, time):
    location = LocationInfo(latitude=lat, longitude=lon)
    elevation_angle = 90 - zenith(location.observer, time, True)

    return elevation_angle

def get_location():
    data = requests.get("https://ipinfo.io/json").json()
    latitude, longitude = map(float, data["loc"].split(","))

    return latitude, longitude

# def get_temperature_shift_percentage(elevation_angle):
#     if elevation_angle <= 0:
#         return 1
#     else:
#         return 1 - math.sin(math.radians(elevation_angle))

def get_night_shift(elevation_angle):
    return 1 - 1 / (1 + math.exp(-(elevation_angle - 10) / 3))

def get_temperature(night_shift):
    return day_temp + (night_temp - day_temp) * night_shift

GAMMA_FACTOR = 2.2

def get_brightness(night_shift):
    return 1 - night_dim_percent * math.pow(night_shift, GAMMA_FACTOR) # Gamma function

def set_display_appearance(rgbScale, brightness):
    x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))
    xf86vm = ctypes.cdll.LoadLibrary(ctypes.util.find_library("Xxf86vm"))

    x11.XOpenDisplay.restype = ctypes.c_void_p
    display = x11.XOpenDisplay(None)

    screen = x11.XDefaultScreen(display)

    size = ctypes.c_int()
    xf86vm.XF86VidModeGetGammaRampSize(display, screen, ctypes.byref(size))

    n = size.value

    r = [int(65535 * (i / n) * rgbScale[0] * brightness) for i in range(n)]
    g = [int(65535 * (i / n) * rgbScale[1] * brightness) for i in range(n)]
    b = [int(65535 * (i / n) * rgbScale[2] * brightness) for i in range(n)]

    array_type = ctypes.c_ushort * n
    r_arr = array_type(*r)
    g_arr = array_type(*g)
    b_arr = array_type(*b)

    xf86vm.XF86VidModeSetGammaRamp(display, screen, n, r_arr, g_arr, b_arr)

def update():
    current_time = datetime.now(timezone.utc)
    latitude, longitude = get_location()
    elevation_angle = get_sun_elevation_angle(latitude, longitude, current_time)

    night_shift = get_night_shift(elevation_angle)
    temperature = get_temperature(night_shift)
    rgbScale = get_rgb_from_temp(temperature)
    brightness = get_brightness(night_shift)

    print(rgbScale)

    print(elevation_angle)

    set_display_appearance(rgbScale, brightness)

while True:
    update()

    time.sleep(60)