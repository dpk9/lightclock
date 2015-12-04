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
import ntplib
import time
import pytz

from geopy.geocoders import GoogleV3  # for finding coords of place names

YES_LIST = ["", "y", "ye", "yes"]
NO_LIST = ["n", "no"]


def main(address, coords=None, time_var=None, date=None):
    try:
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

        tad = time_and_date
        tad = datetime.datetime(tad[0], tad[1], tad[2], tad[3], tad[4], tad[5])
        # convert the time_and_date from localized timezone time to UTC time
        utc_tad = localToUtc(tad, tz)
        print "utc_tad {}".format(utc_tad)

        # Make an observer object for ephem at given location and date/time
        observer = ephem.Observer()
        observer.lat, observer.lon = str(coords[0]), str(coords[1])
        observer.date = utc_tad.strftime("%Y/%m/%d %H:%M:%S")
        print observer

        # Make a sun object and connect it to the observer
        sun = ephem.Sun()
        sun.compute(observer)

        next_sunrise = str(observer.next_rising(sun))
        next_sunrise_utc = datetime.datetime.strptime(next_sunrise,
                                                      "%Y/%m/%d %H:%M:%S")
        print type(next_sunrise_utc)
    except:
        raise


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
    return local_tz.normalize(local)


def setLocation(city=None, lat_lon=None):
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
            confirm_city = raw_input('Is your city "{}"? [y or n] '
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

    print args



    main(address=address, coords=coords, time_var=time_var, date=date)
