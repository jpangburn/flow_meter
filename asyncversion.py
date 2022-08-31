from picozero import pico_led, pico_temp_sensor

import network
import time
import ntptime
import machine
import socket

from machine import Pin
import uasyncio as asyncio

import rp2

import wificonfig
# set country code for wifi to work better
rp2.country(wificonfig.COUNTRY_CODE)
# setup wifi as a station (client)
ssid = wificonfig.SSID
password = wificonfig.PASSWORD
wlan = network.WLAN(network.STA_IF)
# sometimes it's connected between runs, disconnect it and don't care if that fails
try:
    wlan.disconnect()
except:
    pass

# designate the pin to watch the flow
flow_meter_pin_id = 0
# how many ticks per gallon
ticks_per_gallon = 3028

# flow meter count
flow_meter_count = 0
# flow meter start time
flow_meter_start_time = None
# latest ticks per minute
latest_ticks_per_minute = -1
# ticks per last seven days (default to -1)
ticks_per_day = [-1.0 for i in range(7)]


# When the flow meter pin sees a rising edge, increment the flow count by 1
def flow_rising_edge(p):
    global flow_meter_count
    # increment the count
    flow_meter_count += 1

# make the pin an input pin, defaults to pull-up which shouldn't matter
flow_meter_pin = machine.Pin(flow_meter_pin_id, Pin.IN, Pin.PULL_DOWN)
# attach irq to the pin
flow_meter_pin.irq(flow_rising_edge)

# helper to convert ticks to gallons
def ticks_to_gallons(ticks):
    return ticks / ticks_per_gallon

# every time you call this it returns false except for once when the date changes, then it's true once
previous_hour = -1
def is_it_a_new_day():
    global previous_hour
    # get the current hour in local time using PDT (GMT-7) (the localtime call counter-intuitively gives GMT time)
    gmt_hour = time.localtime()[3]
    local_hour = (24 + gmt_hour + int(wificonfig.GMT_OFFSET))%24
    # if the previous hour is not equal to the current hour AND the current hour is 0 then it's a new day
    if previous_hour != local_hour:
        previous_hour = local_hour
        if local_hour == 0:
            return True
    # in all other cases return False
    return False

# run this every minute to show the latest gallons per minute
# and also use this call to detect when we've switched to a new day and do the latest gallons per day
last_flow_meter_count_minute = None
def update_latest_ticks_per_minute():
    global last_flow_meter_count_minute, latest_ticks_per_minute
    if last_flow_meter_count_minute is not None:
        latest_ticks_per_minute = flow_meter_count - last_flow_meter_count_minute
    last_flow_meter_count_minute = flow_meter_count
    print(f'executed update_latest_ticks_per_minute with {latest_ticks_per_minute} (or {ticks_to_gallons(latest_ticks_per_minute):.1f} gallons) at {time.localtime()[3]:02}:{time.localtime()[4]:02} GMT')

# run this every day to show the latest gallons per day
last_flow_meter_count_day = None
def update_latest_ticks_per_day():
    global last_flow_meter_count_day, ticks_per_day
    if last_flow_meter_count_day is not None:
        # move all the current counts back a day
        for i in range(5,-1,-1):
            ticks_per_day[i+1] = ticks_per_day[i]
        # set today's value
        ticks_per_day[i] = flow_meter_count - last_flow_meter_count_day
    last_flow_meter_count_day = flow_meter_count
    print(f'executed update_latest_ticks_per_day at {time.localtime()[3]:02}:{time.localtime()[4]:02} GMT')
    


# define webpage content
def webpage(error_message=''):
    #Template HTML
    html = f"""
            <!DOCTYPE html>
              <head>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Well Flow Monitor</title>
    <link rel="stylesheet" href="/static/style.css">
    
  
<script language="javascript">
window.setTimeout(function(){{
// write in the various things we want to display
document.getElementById('currentTime').innerHTML = new Date({time.time() * 1000});
document.getElementById('startTime').innerHTML = new Date({flow_meter_start_time * 1000});
}},5);
</script>

  </head>
<body>
<nav>
  <h1>Well Flow Monitor</h1>
</nav>
<section class="content">
  <header>
    
  <h1>Flow Data</h1>

  </header>
  
  
  <article>
            <div class="{'flash' if len(error_message) > 1 else ''}">{error_message}</div>
            <p>Flow count is {flow_meter_count} which is {ticks_to_gallons(flow_meter_count):.1f} gallons</p>
            <p>Latest gallons per minute {ticks_to_gallons(latest_ticks_per_minute):.2f}</p>
            <p>Latest gallons per day """ + str([f"{ticks_to_gallons(x):.1f}" for x in ticks_per_day]) + f"""</p>
            <p>Time running is {time.time() - flow_meter_start_time} seconds, or {(time.time() - flow_meter_start_time)/86400:.1f} days</p>
            <p>Current time is <span id="currentTime"></span>, up since <span id="startTime"></span></p>
            <p>Pico temperature is {pico_temp_sensor.temp * 9/5 + 32:.0f} &deg;F</p>
            
            <form action="./">
                <input type="submit" value="Refresh" />
            </form>
            <p></p>
            <form action="./changedivisor">
                <label for="ticksPerGallon">Ticks per gallon:</label>
                <input type="number" id="ticksPerGallon" name="ticksPerGallon" min="2500" max="3500" step="1" value="{ticks_per_gallon}"/>
                <input type="submit" value="Change Divisor" />
            </form>
    </article>
    </section>
            </body>
            </html>
            """
    return str(html)

# define stylesheet content for the webpage
def stylesheet():
    stylesheet = """
html { font-family: sans-serif; background: #eee; padding: 1rem; }
body { max-width: 960px; margin: 0 auto; background: white; }
h1 { font-family: serif; color: #377ba8; margin: 1rem 0; }
a { color: #377ba8; }
th, td {
    padding-left: 10px;
    padding-right: 10px;
  }
hr { border: none; border-top: 1px solid lightgray; }
nav { background: lightgray; display: flex; align-items: center; padding: 0 0.5rem; }
nav h1 { flex: auto; margin: 0; }
nav h1 a { text-decoration: none; padding: 0.25rem 0.5rem; }
nav ul  { display: flex; list-style: none; margin: 0; padding: 0; }
nav ul li a, nav ul li span, header .action { display: block; padding: 0.5rem; }
.content { padding: 0 1rem 1rem; }
.content > header { border-bottom: 1px solid lightgray; display: flex; align-items: flex-end; }
.content > header h1 { flex: auto; margin: 1rem 0 0.25rem 0; }
.flash { margin: 1em 0; padding: 1em; background: #cae6f6; border: 1px solid #377ba8; }
.conversation > header { display: flex; align-items: flex-end; font-size: 0.85em; }
.conversation > header > div:first-of-type { flex: auto; }
.conversation > header h1 { font-size: 1.5em; margin-bottom: 0; }
.conversation .about { color: slategray; font-style: italic; }
.conversation .body { white-space: pre-line; }
.autoconversation { background: yellow; }
.content:last-child { margin-bottom: 0; }
.content form { margin: 1em 0; display: flex; flex-direction: column; }
.content label { font-weight: bold; margin-bottom: 0.5em; }
.content input, .content textarea { margin-bottom: 1em; }
.content textarea { min-height: 12em; resize: vertical; }
input.danger { color: #cc2f2e; }
input[type=submit] { align-self: start; min-width: 10em; }
"""
    return str(stylesheet)



async def connect_to_network(get_ntp=True):
    wlan.active(True)
    #wlan.config(pm = 0xa11140) # Disable power-save mode
    wlan.connect(ssid, password)
    max_wait = 10

    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('waiting for connection...')
        await asyncio.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError('network connection failed')
    else:
        print('connected')
        status = wlan.ifconfig()
        print('ip = ' + status[0])
        
        # set time to NTP time if desired
        if get_ntp:
            ntptime.settime()
        
        # flash the led to indicate successful connection, except if we're operating this function asynchronously
        for i in range(3):
            pico_led.on()
            await asyncio.sleep(0.3)
            pico_led.off()
            await asyncio.sleep(0.3)

async def serve_client(reader, writer):
    global ticks_per_gallon
    print("Client connected")
    request_line = await reader.readline()
    print("Request:", request_line)
    # We are not interested in HTTP request headers, skip them 
    while await reader.readline() != b"\r\n":
        pass

    request = str(request_line)
    content_type = 'text/html'
    response = 'Error: no response set'
    if request.find('/static/style.css') != -1:
        response = stylesheet()
        content_type = 'text/css'
    elif request.find('/changedivisor') != -1:
        # ticks per gallon change request
        # try to parse it out, where request looks like b'GET /changedivisor?ticksPerGallon=3032 HTTP/1.1\r\n'
        # so just split on the = sign, and grab the second part, then get the first 4 characters and parse as an int
        # If that fails then just ignore this
        try:
            ticks_per_gallon = int(request.split('=')[1][0:4])
            # generate normal response
            response = webpage()
        except Exception as e:
            error_message = f'Got error updating ticks per gallon: {e}'
            # generate error page
            response = webpage(error_message)
    else:
        # normal request for content
        # generate web page
        response = webpage()
        
    # send the HTTP response header and response content
    writer.write(f'HTTP/1.0 200 OK\r\nContent-type: {content_type}\r\n\r\n')
    writer.write(response)
    
    await writer.drain()
    await writer.wait_closed()
    print("Client disconnected")
    
async def update_gallons_data():
    global flow_meter_start_time
    global flow_meter_count
    # set the flow meter start time
    flow_meter_start_time = time.time()
    # reset flow count
    flow_meter_count = 0
    # start the first day off as 0 gallons
    update_latest_ticks_per_day()
    # loop forever
    while True:
        # update gallons per minute every minute
        update_latest_ticks_per_minute()
        # is it a new day?  If so update latest gallons per day too
        if is_it_a_new_day():
            update_latest_ticks_per_day()
        # sleep for a minute
        await asyncio.sleep(60)
        
async def reset_network_connection():
    while True:
        # the network status is not trustworthy, so if you ask "if wlan.status() != 3:"
        # and expect it to change when the network is down you'll be disappointed
        # so just reset the wifi every hour and hope for the best
        await asyncio.sleep(3600)
        # fully disconnect it to restart
        try:
            wlan.disconnect()
        except:
            pass
        # not sure if it helps to sleep a bit here, but if it does it won't hurt to be offline for 10 seconds per hour
        await asyncio.sleep(10)
        # try to reconnect, but don't bother to reset NTP time
        try:
            await connect_to_network(False)
            print('reset_network_connection successfully reconnected to network')
        except Exception as e:
            print(f'reset_network_connection failed to reconnect due to exception: {e}')

async def main():
    print('Connecting to Network...')
    await connect_to_network()
        
    print('Setting up webserver...')
    asyncio.create_task(asyncio.start_server(serve_client, "0.0.0.0", 80))
    
    print('Starting update task')
    asyncio.create_task(update_gallons_data())
    
    print('Starting network watcher')
    asyncio.create_task(reset_network_connection())
    
    while True:
        pico_led.on()
        await asyncio.sleep(0.25)
        pico_led.off()
        await asyncio.sleep(5)

try:
    asyncio.run(main())
finally:
    asyncio.new_event_loop()