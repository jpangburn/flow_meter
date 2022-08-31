# flow_meter

This project implements a water flow meter using a Raspberry Pi Pico W and a digital flow meter sensor.  The web interface shows your water flow over the past week similar to this:

<img width="972" alt="Screen Shot 2022-08-31 at 1 26 52 PM" src="https://user-images.githubusercontent.com/4357286/187775713-a34ab314-ba27-48c3-b34c-ed401d039b93.png">

It shows:
- total amount through the meter
- current flow rate (mine is zero because our pump shuts off for the day when the tank is full)
- total gallons for the past week (yesterday is first in the list and gets pushed one slot to the right each day)
- other fields are self explanatory except for the divisor.  There is an unknown amount of ticks on the sensor for each gallon- I made it configurable because I imagine the sensors are not all built perfectly.  Some might have 3100 ticks per gallon, some might have 2950, who knows.  For my house there's an analog meter on the well, so I just set the divisor so that the gallons on this tool match the gallons on the analog meter.  If you have no meter to check against, just use my value and it'll at least be in the ballpark.

## The sensor

I used this one https://smile.amazon.com/DIGITEN-Sensor-Switch-Flowmeter-Counter/dp/B00VKATCRQ ![51qKoCiNccL _AC_UY436_QL65_](https://user-images.githubusercontent.com/4357286/187770643-d2fe6fec-3fc5-4443-a0b6-2064f9c85392.jpg)

It produces a nice clean square wave.  Checked it with an oscilloscope and there was no noise or spikes in the signal, and although it says 5-18 volts it worked fine on the 3.3 volts that the pico wants.  It's been working for a couple weeks on my well pump so can't speak to its longevity yet but so far so good.

You can use any sensor where you can get it to produce a clean wave where the peak is 3.3v (doesn't need to be square) that the pico can count.

## How to use

1. Get the latest MicroPython for the Pico W installed on your pico and make sure it works normally.  Use the `Tools->Manage Packages` button to install the `picozero` package on your pico.

2. Download the source code from this project.

3. Open in Thonny (you can use whatever IDE you like, but Thonny is easy to upload files from)

4. Edit the wificonfig.py file which looks like this:

```
COUNTRY_CODE = 'US' # change to your country code if not US

SSID = 'your ssid here'
PASSWORD = 'your wifi password here'

GMT_OFFSET = '-7' # PDT is -7
```
Put in the SSID and password for your own wifi. Change the country code if you're outside the US. Use the timezone where the meter is as the GMT_OFFSET- this is used by the program to decide when a new day has occured so it can display the gallons per day.  Note that MicroPython does not have timezone support so there's no easy way to update the time for daylight savings (if your area still does that silliness, mine does sadly).

5. Use `File->Save Copy...` to save this file to the pico with the name 'wificonfig.py'

6. Open the `asyncversion.py` file in Thonny and run it to make sure it works.  You should see output like this:

```
>>> %Run -c $EDITOR_CONTENT
Connecting to Network...
waiting for connection...
waiting for connection...
waiting for connection...
connected
ip = 192.168.2.113
Setting up webserver...
Starting update task
Starting network watcher
executed update_latest_ticks_per_day at 19:45 GMT
executed update_latest_ticks_per_minute with -1 (or -0.0 gallons) at 19:45 GMT
```

If you see something else, check the `errors` section below.

7. Once the previous step was successful, you need to use `File->Save Copy...` to save this file to the pico as main.py (i.e. the file `asyncversion.py` gets saved to the pico as `main.py` because that's what MicroPython looks for.  If it's done correctly your save window on the Pico W should look like: <img width="801" alt="Screen Shot 2022-08-31 at 1 07 33 PM" src="https://user-images.githubusercontent.com/4357286/187772390-3725edf0-0f6f-4eb9-9ed8-fae04ef03ed2.png">

8. Hook up the sensor so the ground is connected to a pico ground pin, the positive is connected to the pico's 3.3v output pin which is labeled `3V3(OUT)` on the pinout, and the yellow sensor lead is connected to the `GP0` pin, which is pin #1 (the top left pin).

9. Blow in the sensor so it spins the measuring blades (you'll hear it spin) and then make sure it registers some fraction of a gallon on the next minute update.  The line `executed update_latest_ticks_per_minute with -1 (or -0.0 gallons) at 19:45 GMT` should go from -1 to some positive integer value.

10. Provide power to the pico and install it wherever you want to measure your water flow.

## Web interface

Having this hooked to your computer would be pretty useless, so there's a web interface.  Look at the IP address assigned to the Pico W in the output where it says something like `ip = 192.168.2.113`.  Then go to http://192.168.2.113 (except whatever your IP address is) or you can try http://pybd if you have DNS setup correctly through DHCP on your local network (many people do not so this likely won't work for you) as `pybd` is the pico's default name.

I suggest you use your router settings to assign the pico an IP address (and/or different DNS name) so you don't have to worry if the IP changes from DHCP.

## Troubleshooting

To troubleshoot, make sure to have it hooked up to Thonny so you can see the output.

### Wifi error

Check your SSID and PASSWORD values in the wificonfig.py file and make sure you saved it to the pico.

###   File "ntptime.py", line 24, in time
###    OSError: [Errno 110] ETIMEDOUT

This error happens if your pico can't connect to an NTP server to get the current GMT time.  Make sure you have internet access from your router, but otherwise just try again- this seems to fail occasionally but is only called once when the program starts.

### ImportError: no module named 'wificonfig'

You didn't save the wificonfig.py file to the pico

### ImportError: no module named 'picozero'

You didn't install the picozero package

### When I blow in the sensor I hear it spin, but the `executed update_latest_ticks_per_minute with -1 (or -0.0 gallons) at 19:45 GMT` line always says `-1` for ticks.

If you have an oscilloscope, connect it to pin 1 (GP0) and ground.  Blow in the sensor- you should see a nice square wave.  If not (and you used the same sensor) then make sure you hooked up positive to the `3V3(OUT)` pin.

If you don't have an oscilloscope, you can use a voltmeter.  Blow in the sensor until it spins, and watch the volts, it should go up from zero and then stop at either 0 or 3.3.  Repeat until you see it stop at 3.3 (it's a 50% cycle so half the time it's high and half the time it's low so odds are you'll see 3.3 pretty soon).  If the volts don't change and it never stops at 3.3 then it's hooked up wrong (or you used a different sensor that works differently).
