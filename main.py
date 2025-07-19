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

day_temp = 6000 # natural white light
night_temp = 4000 # orange colour
night_dim_percent = 0.4

def kelvin_to_rgb(temperature):
    """Convert a color temperature in Kelvin to normalized RGB (0 to 1)."""
    
    temp = temperature / 100.0
    
    # Calculate RGB components
    if temp <= 66:
        r = 1.0
        g = 0.2908 * math.log(temp) - 1.1196
        if temp <= 19:
            b = 0.0
        else:
            b = 0.1385 * math.log(temp - 10) - 0.3050
    else:
        r = 0.3297 * (temp - 60) ** -0.133204
        g = 0.2881 * (temp - 60) ** -0.075515
        b = 1.0
    
    # Clip values to be within 0 to 1
    r = min(1.0, max(0.0, r))
    g = min(1.0, max(0.0, g))
    b = min(1.0, max(0.0, b))
    
    return (r, g, b)

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

def get_temperature_percentage(elevation_angle):
    return 1 - 1 / (1 + math.exp(-(elevation_angle - 10) / 3))

def set_display_appearance(gammaRed, gammaGreen, gammaBlue, brightness):
    x11 = ctypes.cdll.LoadLibrary(ctypes.util.find_library("X11"))
    xf86vm = ctypes.cdll.LoadLibrary(ctypes.util.find_library("Xxf86vm"))

    x11.XOpenDisplay.restype = ctypes.c_void_p
    display = x11.XOpenDisplay(None)

    screen = x11.XDefaultScreen(display)

    size = ctypes.c_int()
    xf86vm.XF86VidModeGetGammaRampSize(display, screen, ctypes.byref(size))

    n = size.value

    r = [int(65535 * (i / n) * gammaRed * brightness) for i in range(n)]
    g = [int(65535 * (i / n) * gammaGreen * brightness) for i in range(n)]
    b = [int(65535 * (i / n) * gammaBlue * brightness) for i in range(n)]

    array_type = ctypes.c_ushort * n
    r_arr = array_type(*r)
    g_arr = array_type(*g)
    b_arr = array_type(*b)

    xf86vm.XF86VidModeSetGammaRamp(display, screen, n, r_arr, g_arr, b_arr)

def update():
    current_time = datetime.now(timezone.utc)
    latitude, longitude = get_location()
    elevation_angle = get_sun_elevation_angle(latitude, longitude, current_time)

    temperature_percentage = get_temperature_percentage(elevation_angle)
    temperature = day_temp + (night_temp - day_temp) * temperature_percentage
    gamma_scale = temperature / NEUTRAL_TEMP
    brightness_scale = 1 - night_dim_percent * temperature_percentage

    print(elevation_angle)

    set_display_appearance(1, gamma_scale, gamma_scale, brightness_scale)

    print(temperature, kelvin_to_rgb(temperature))

while True:
    update()

    time.sleep(60)