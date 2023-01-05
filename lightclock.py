"""
lightclock.py

David Kalish
CS50 Fall 2015

Automatedly control a light on a schedule based to simulate the daylight time of
a specific place in the world.  During morning twilight hours, lights gradually
dim on. At sunrise, lights are fully on all day. During evening twilight, dim
off. At the end of evening twilight, turn off fully overnight.

"""

import datetime
import ephem
import math
import time
import pytz

import RPi.GPIO as GPIO

from geopy.geocoders import GoogleV3

YES_LIST = ["", "y", "ye", "yes"]
NO_LIST = ["n", "no"]


TIMER = 60.0
TWILIGHT_ALT = -18  # astronomical twilight
# TWILIGHT_ALT = -12  # nautical twilight
# TWILIGHT_ALT = -6   # civil twilight



def main(address, coords=None, time_var=None, date=None):
    """
    Using an address or coordinates, and optionally a starting time and/or a
    starting date, simulate the sunlight patterns of anyplace in the world.
    Refreshes every minute (or value of TIMER), dimming the light on/off during
    twilight hours (when the sun is 18, 12, or 6 degrees below horizon for
    astronomical, nautical, or civil twilight, respectively)
    """
    try:
        PWM_pin = initRaspPi()
        # process the location to coords, get timezone name
        coords, tz = setLocation(city=address, lat_lon=coords)
        print("coords = {}\ntz = {}".format(coords, tz))

        # default to localtime
        time_and_date = list(time.localtime())
        # insert given time if given
        if time_var:
            time_var = list(time.strptime(time_var, "%H:%M"))

            # hour = index 3, minute = index 4
            for i in [3, 4]:
                time_and_date[i] = time_var[i]
        # insert given date if given
        if date:
            date = list(time.strptime(date, "%m/%d/%Y"))
            # [yr, mon, day, SKIP, SKIP, SKIP, wday, yday, dst]
            for i in [0, 1, 2, 6, 7, 8]:
                time_and_date[i] = date[i]

        start_tad = time_and_date
        # get the offset from target time to current time
        tad_offset = time.time() - time.mktime(start_tad)
        print("time diff {}".format(tad_offset))

        # Make an observer object for ephem at given location and date/time
        observer = ephem.Observer()
        observer.lat, observer.lon = str(coords[0]), str(coords[1])
        # make a sun object
        sun = ephem.Sun()

        # prev_alt init so it has something to start with
        prev_altitude = 900

        # Loop every minute (or TIMER seconds if TIMER != 60)
        while True:
            # for the timer
            tick = time.time()
            print("tick {}".format(tick))

            # calc the new time and date
            tad = list(time.localtime(time.time() - tad_offset))
            tad = datetime.datetime(tad[0], tad[1], tad[2], tad[3], tad[4], tad[5])
            # convert the time_and_date from localized timezone time to UTC time
            utc_tad = localToUtc(tad, tz)
            print("utc_tad {}".format(utc_tad))

            # update the observer's tad
            observer.date = utc_tad.strftime("%Y/%m/%d %H:%M:%S")
            print(observer)

            # observe the sun
            sun.compute(observer)

            # calculate sun altitude in degrees
            altitude = int(math.degrees(sun.alt))
            print("altitude {}".format(altitude))

            # sunlight adjustment time!
            # see if light is above the horizon (full daylight)
            if altitude >= 0:
                # light will be on fully, just make it 0
                altitude = 0
            # see if light is below twilight altitude (full night)
            elif altitude < TWILIGHT_ALT:
                # light will be off fully, just make it twilight
                altitude = TWILIGHT_ALT
            # don't need to check for light inside the twilight range because it
            # that will be caught in the altitude-change check in the next step

            # look for a 1 degree change in altitude
            if abs(altitude - prev_altitude) > 0:
                lightControl(PWM_pin, altitude)

            # update the prev_altitude
            prev_altitude = altitude

            # sleep the rest of the 60 seconds
            time.sleep(TIMER - ((time.time() - tick) % TIMER))

    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        PWM_pin.stop()
        GPIO.cleanup()
        print("Exiting cleanly")
        return

    except:
        raise


def initRaspPi():
    """
    Initialize the Raspberry Pi GPIO for PWM
    """
    GPIO.setmode(GPIO.BOARD)
    # pin 21 is output pin
    GPIO.setup(21, GPIO.OUT)
    # initialize PWM duty cycle to 0 to start
    pin = GPIO.PWM(21, 0.01)
    # start the PWM
    pin.start(0)
    return pin


def lightControl(pin, altitude):
    """
    Change the duty cycle of the PWM pin
    """
    # calc the duty cycle %
    duty_cycle = int(abs(100 * (abs(float(TWILIGHT_ALT) - float(altitude))
                                / float(TWILIGHT_ALT))))

    if duty_cycle == 0:
        duty_cycle = 0.01
    elif duty_cycle == 100:
        duty_cycle = 99.9

    print("duty_cycle = {}".format(duty_cycle))

    # set the duty cycle
    pin.ChangeDutyCycle(duty_cycle)
    return


def localToUtc(local_tad, tz):
    """
    Convert a locally timezoned datetime.datetime to UTC datetime.datetime
    """
    local = pytz.timezone(tz)
    local_tad = local.localize(local_tad)
    utc_tad = local_tad.astimezone(pytz.utc)
    return utc_tad


def utcToLocal(utc_tad, tz):
    """
    convert a UTC datetime.datetime to a locally timezoned datetime.datetime
    """
    local = pytz.timezone(tz)
    local_tad = utc_tad.replace(tzinfo=pytz.utc).astimezone(local)
    return local.normalize(local_tad)


def setLocation(city=None, lat_lon=None):
    """
    Turn the given city into a lat/lon, or verify the given lat/lon.
    Find the timezone of the location.
    """
    # make sure it's a valid location
    # either give a city or a lat/lon
    if city and lat_lon:
        raise ValueError("Bad location.  Expect either `city` OR "
                         "[`lat`, `lon`]")
    # if not a city name, make sure lat_lon is valid
    geolocator = GoogleV3(timeout=10)
    if not city:
        lat_lon_err = False
        # Make sure lat_lon is list/tuple
        if not isinstance(lat_lon, (list, tuple)):
            raise TypeError("lat_lon should be a list or tuple.")
        # if lat/lon aren't in -90 <= lat <= 90 and -180 < lon <= 180, raise
        lat, lon = lat_lon
        if lat and lon:
            if not (-90 <= lat and lat <= 90):
                lat_lon_err = True
            if not (-180 < lon and lon <= 180):
                lat_lon_err = True
        # if if lat or lon is missing, raise
        else:
            lat_lon_err = True
        if lat_lon_err:
            raise ValueError("Given lat = {}, lon = {}. "
                             "Needs -90 < lat < 90, -180 < lon < 180."
                             "".format(lat, lon))
    # if it's a city, get the lat/lon
    else:
        city_long, lat_lon = geolocator.geocode(city)
        while True:
            # Ask if we have interpreted the correct city
            confirm_city = input('Is your city "{}"? [y or n] '
                                     ''.format(city_long))
            if confirm_city.lower().strip() in YES_LIST:
                lat, lon = lat_lon
                break
            elif confirm_city.lower().strip() in NO_LIST:
                raise ValueError("Try again with a more specific city name.")
            else:
                print("Invalid confirmation '{}'".format(confirm_city))
    tz = str(geolocator.timezone((lat, lon)))

    return [lat, lon], tz


if __name__ == "__main__":
    # parse some arguments!
    from argparse import ArgumentParser
    parser = ArgumentParser()

    # Either address or coords is required.
    location_group = parser.add_mutually_exclusive_group(required=True)
    location_group.add_argument("-a", "--address",
                                help='Set the location with an address. \
                                    Address can be a specific address, a city \
                                    name, a city+state, a country, etc.',
                                action="store")
    location_group.add_argument("-c", "--coords",
                                help='Set the location as a set of LATITUDE \
                                    LONGITUDE coordinates.',
                                action="store",
                                nargs=2,
                                metavar=("LAT", "LON"),
                                type=float)

    # Time and date are both optional. If only one is given, use current for
    # other.
    parser.add_argument("-t", "--time",
                        help='Set time. Format is 24-hr "HH:MM". Default to \
                            current time.',
                        action="store")
    parser.add_argument("-d", "--date",
                        help='Set the date. Format is MM/DD/YYYY. Default to \
                            current date.',
                        action="store")

    args = parser.parse_args()

    # Save the args as vars
    address = args.address
    coords = args.coords
    time_var = args.time
    date = args.date

    print(args)

    main(address=address, coords=coords, time_var=time_var, date=date)
# end if __name__ == "__main__"
