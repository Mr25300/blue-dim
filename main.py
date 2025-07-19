from datetime import datetime, timezone
from astral import LocationInfo
from astral.sun import zenith
import requests
import platform
# import subprocess
import ctypes
import ctypes.util
import time

NEUTRAL_TEMP = 6500
SHIFT_START_ANGLE = 15
SHIFT_END_ANGLE = -5

day_temp = 6000 # natural white light
night_temp = 4000 # orange colour
night_dim_percent = 0.4

def get_sun_elevation_angle(lat, lon, time):
    location = LocationInfo(latitude=lat, longitude=lon)
    elevation_angle = 90 - zenith(location.observer, time, True)

    return elevation_angle

def get_location():
    data = requests.get("https://ipinfo.io/json").json()
    latitude, longitude = map(float, data["loc"].split(","))

    return latitude, longitude

def get_night_temperature_shift(elevation_angle):
    if elevation_angle >= SHIFT_START_ANGLE:
        return 0
    elif elevation_angle <= SHIFT_END_ANGLE:
        return 1
    else:
        return 1 - (elevation_angle - SHIFT_END_ANGLE) / (SHIFT_START_ANGLE - SHIFT_END_ANGLE)

# def get_primary_output_linux():
#     result = subprocess.run(["xrandr", "--query"], capture_output=True, text=True)
#     lines = result.stdout.splitlines()

#     for line in lines:
#         if " connected" in line:
#             output_name = line.split()[0]

#             return output_name
    
#     return None

# def set_display_appearance(gammaR, gammaG, gammaB, brightness):
#     os_name = platform.system()

#     if os_name == "Linux":
#         output_name = get_primary_output_linux()

#         if output_name:
#             subprocess.run(["xrandr", "--output", output_name,
#                             "--gamma", f"{gammaR}:{gammaG}:{gammaB}",
#                             "--brightness", str(brightness)
#                             ])
        
#     elif os_name == "Windows":
#         print("Functionality not yet implemented.")

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

    shift_percentage = get_night_temperature_shift(elevation_angle)
    temperature = day_temp + (night_temp - day_temp) * shift_percentage
    gamma_scale = temperature / NEUTRAL_TEMP
    brightness_scale = 1 - night_dim_percent * shift_percentage

    set_display_appearance(1, gamma_scale, gamma_scale, brightness_scale)

while True:
    update()

    time.sleep(60)