import network
import socket
from machine import Pin, time_pulse_us, SoftI2C
import time
import dht
from time import sleep, sleep_us
from machine_i2c_lcd import I2cLcd
import ure

led = Pin(2, Pin.OUT)

d = dht.DHT22(Pin(4))   # Using DHT22 on GPIO4
TRIG = Pin(27, Pin.OUT)
ECHO = Pin(26, Pin.IN)

I2C_ADDR = 0x27
i2c = SoftI2C(sda=Pin(21), scl=Pin(22), freq=400000)
lcd = I2cLcd(i2c, I2C_ADDR, 2, 16)

ssid = 'Robotic WIFI'
password = 'rbtWIFI@2025'

wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(ssid, password)

print("Connecting to WiFi...", end="")
while not wlan.isconnected():
    print(".", end="")
    time.sleep(1)
print("\nConnected! IP:", wlan.ifconfig()[0])

def get_sensor_data():
    try:
        d.measure()
        temp = d.temperature()
        hum = d.humidity()
    except:
        temp, hum = None, None

    try:
        dist = distance_cm()
    except:
        dist = None

    return temp, hum, dist
def distance_cm():
    TRIG.off(); sleep_us(2)
    TRIG.on();  sleep_us(10)
    TRIG.off()
    t = time_pulse_us(ECHO, 1, 30000)  # timeout 30ms
    if t < 0:
        return None
    return (t * 0.0343) / 2.0

def lcd_scroll_text(text, row=0, delay=0.4):
    """ Scrolls text if longer than 16 chars """
    lcd.move_to(0, row)
    if len(text) <= 16:
        # Pad manually since MicroPython str has no ljust
        text_to_show = text + ' ' * (16 - len(text))
        lcd.putstr(text_to_show)
    else:
        for i in range(len(text) - 15):
            lcd.move_to(0, row)
            lcd.putstr(text[i:i+16])
            time.sleep(delay)


def web_page():
    temp, hum, dist = get_sensor_data()
    gpio_state = "ON" if led.value() == 1 else "OFF"

    html = """<html><head>
    <title>ESP Web Server</title>
    <style>
    html{font-family: Helvetica; text-align: center;}
    .button{padding: 12px 28px; margin: 5px; font-size: 18px; border:none; border-radius:6px; cursor:pointer;}
    .on{background-color: green; color:white;}
    .off{background-color: red; color:white;}
    .lcd{background-color: #4286f4; color:white;}
    input[type=text]{padding:10px; width:60%; font-size:16px;}
    </style></head><body>
    <h1>ESP32 Web Server</h1>
    <p>GPIO state: <strong>""" + gpio_state + """</strong></p>
    <p><a href="/?led=on"><button class="button on">LED ON</button></a>
    <a href="/?led=off"><button class="button off">LED OFF</button></a></p>
    <h2>Sensor Readings</h2>
      <p>Temperature: """ + (str(temp) if temp else "N/A") + """ &#8451;</p>
      <p>Humidity: """ + (str(hum) if hum else "N/A") + """ %</p>
      <p>Distance: """ + (str(dist) if dist else "No echo") + """ cm</p>
    <h2>LCD Control</h2>
    <p><a href="/?show=distance"><button class="button lcd">Show Distance</button></a>
    <a href="/?show=temp"><button class="button lcd">Show Temp</button></a></p>
    <h2>Send Custom Text</h2>
    <form action="/" method="get">
      <input type="text" name="msg" placeholder="Enter text here">
      <input type="submit" value="Send" class="button lcd">
    </form>
    </body></html>"""
    return html

# --- Web Server ---
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('', 80))
s.listen(5)

while True:
    conn, addr = s.accept()
    print('Got a connection from %s' % str(addr))
    request = conn.recv(1024).decode()
    print('Content = %s' % request)

    # --- LED Control ---
    if '/?led=on' in request:
        led.value(1)
    if '/?led=off' in request:
        led.value(0)

    # --- LCD Buttons ---
    temp, hum, dist = get_sensor_data()
    if '/?show=distance' in request:
        lcd.clear()
        lcd.move_to(0, 0)
        lcd.putstr("Dist: " + (str(round(dist,1)) + " cm" if dist else "No echo"))
    if '/?show=temp' in request:
        lcd.move_to(0, 1)
        lcd.putstr("Temp: " + (str(round(temp,1)) + " C" if temp else "N/A"))

    # --- Custom Text from Form ---
    match = ure.search(r'GET /\?msg=(.*?) ', request)
    if match:
        user_text = match.group(1)
        if isinstance(user_text, bytes):
            user_text = user_text.decode()
        user_text = user_text.replace('%20', ' ')
        user_text = user_text.replace('+', ' ')
        print("LCD Message:", user_text)
        lcd.clear()
        lcd_scroll_text(str(user_text), row=0)

    # --- Send HTML ---
    response = web_page()
    conn.send('HTTP/1.1 200 OK\n')
    conn.send('Content-Type: text/html\n')
    conn.send('Connection: close\n\n')
    conn.sendall(response.encode())
    conn.close()
