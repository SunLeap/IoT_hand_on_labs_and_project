# main.py -- Smart Plant Monitor (MicroPython) - FINAL FIXED VERSION
import network
import time
import machine
import ujson as json
from machine import Pin, ADC
import dht
import socket

# ----- STATIC VALUES -----
WIFI_SSID     = "V"
WIFI_PASSWORD = "12345678"

TELEGRAM_TOKEN   = "8263293375:AAEwwscx-batgO_sO45LK4Bm_h_YfVj-oOM"
TELEGRAM_CHAT_ID = "-5009748239"

DHT_PIN      = 4
SOIL_ADC_PIN = 33
RELAY_PIN    = 17

SOIL_DRY_THRESHOLD = 2500
SENSOR_INTERVAL_MS = 5000
TELEGRAM_MIN_INTERVAL_S = 30
HTTP_LISTEN_PORT = 80

# ----- GLOBALS -----
sta_if = network.WLAN(network.STA_IF)
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))

soil_adc = ADC(Pin(SOIL_ADC_PIN))
soil_adc.atten(ADC.ATTN_11DB)
soil_adc.width(ADC.WIDTH_12BIT)

relay = Pin(RELAY_PIN, Pin.OUT)
relay.value(0)

CONTROL_MODE = "AUTO"

last_status = {
    "moisture": None,
    "temp": None,
    "humidity": None,
    "pump": False,
    "Pump": "OFF",
    "mode": CONTROL_MODE,
    "ip": None
}

_last_alert_ms = 0  # NEW: ms-based rate limiter for Telegram

# ----- WIFI -----
def wifi_connect(ssid, password, timeout=20):
    sta_if.active(False)
    time.sleep(1)
    sta_if.active(True)
    
    print("Connecting to WiFi...")
    sta_if.connect(ssid, password)
    
    start = time.time()
    while not sta_if.isconnected():
        if time.time() - start > timeout:
            raise OSError("WiFi timeout")
        time.sleep(0.5)

    print("Connected:", sta_if.ifconfig())
    return sta_if.ifconfig()[0]

# ----- SENSOR READ -----
def read_sensors():
    soil = soil_adc.read()
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
        hum = dht_sensor.humidity()
    except:
        temp = None
        hum = None
    return soil, temp, hum

# ----- TELEGRAM -----
try:
    import urequests as requests
except:
    requests = None
    print("WARNING: urequests missing, Telegram disabled")

def send_telegram_message(token, chat_id, text):
    if requests is None:
        print("Telegram disabled - urequests not available")
        return False
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(token)
        payload = "chat_id={}&text={}".format(chat_id, text)
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        r = requests.post(url, data=payload, headers=headers)
        print("Telegram response:", r.status_code)
        ok = r.status_code == 200
        r.close()
        return ok
    except Exception as e:
        print("Telegram error:", e)
        return False

# ----- PUMP -----
def set_pump(on):
    previous = last_status["pump"]
    relay.value(1 if on else 0)
    last_status["pump"] = bool(on)
    last_status["Pump"] = "ON" if on else "OFF"

    print("Pump =", last_status["Pump"])

    # Only send alert on change
    if previous != on:
        msg = "⚡ Pump {}\nMoisture={}".format(
            "ON" if on else "OFF",
            last_status["moisture"]
        )
        if last_status["temp"] is not None:
            msg += "\nTemp={}°C".format(last_status["temp"])
        if last_status["humidity"] is not None:
            msg += "\nHumidity={}%".format(last_status["humidity"])

        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg)

# ----- ROUTING -----
def route(path):
    global CONTROL_MODE

    if path.startswith("/pump/on"):
        set_pump(True)
        return json.dumps(last_status)

    if path.startswith("/pump/off"):
        set_pump(False)
        return json.dumps(last_status)

    if path.startswith("/mode/auto"):
        CONTROL_MODE = "AUTO"
        last_status["mode"] = "AUTO"
        return json.dumps(last_status)

    if path.startswith("/mode/manual"):
        CONTROL_MODE = "MANUAL"
        last_status["mode"] = "MANUAL"
        return json.dumps(last_status)

    if path.startswith("/status"):
        return json.dumps(last_status)

    html = """
    <html><body><h2>Smart Plant Monitor</h2>
    <p>Moisture: {}<br>Temp: {}°C<br>Humidity: {}%<br>Pump: {}<br>Mode: {}</p>
    <p><a href='/pump/on'>Pump ON</a> | <a href='/pump/off'>Pump OFF</a></p>
    <p><a href='/mode/auto'>Auto Mode</a> | <a href='/mode/manual'>Manual Mode</a></p>
    </body></html>
    """.format(
        last_status["moisture"],
        last_status["temp"],
        last_status["humidity"],
        last_status["Pump"],
        last_status["mode"]
    )
    return html

# ----- SERVER -----
def start_server(ip):
    global _last_alert_ms, CONTROL_MODE
    
    addr = socket.getaddrinfo(ip, HTTP_LISTEN_PORT)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    s.settimeout(0.1)

    print("Server started at: http://{}/".format(ip))
    
    last_read = 0

    while True:

        # ----- AUTO LOGIC -----
        if time.ticks_diff(time.ticks_ms(), last_read) > SENSOR_INTERVAL_MS:
            last_read = time.ticks_ms()

            soil, temp, hum = read_sensors()
            last_status["moisture"] = soil
            last_status["temp"] = temp
            last_status["humidity"] = hum

            print("Sensors: moisture={} temp={} humidity={}".format(soil, temp, hum))

            if CONTROL_MODE == "AUTO":
                now = time.ticks_ms()
                time_since_alert = time.ticks_diff(now, _last_alert_ms)

                # Dry → Pump ON
                if soil >= SOIL_DRY_THRESHOLD and not last_status["pump"]:
                    print("Soil DRY - turning pump ON")
                    set_pump(True)

                    if time_since_alert > TELEGRAM_MIN_INTERVAL_S * 1000:
                        msg = "🌱 Soil dry → Pump ON\nMoisture={}".format(soil)
                        if temp is not None:
                            msg += "\nTemp={}°C".format(temp)
                        if hum is not None:
                            msg += "\nHumidity={}%".format(hum)

                        if send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg):
                            _last_alert_ms = now
                            print("Telegram alert sent")
                        else:
                            print("Telegram alert FAILED")

                # Wet → Pump OFF
                elif soil < SOIL_DRY_THRESHOLD and last_status["pump"]:
                    print("Soil WET - turning pump OFF")
                    set_pump(False)

                    if time_since_alert > TELEGRAM_MIN_INTERVAL_S * 1000:
                        msg = "💧 Soil wet → Pump OFF\nMoisture={}".format(soil)
                        if temp is not None:
                            msg += "\nTemp={}°C".format(temp)
                        if hum is not None:
                            msg += "\nHumidity={}%".format(hum)

                        if send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg):
                            _last_alert_ms = now
                            print("Telegram alert sent")
                        else:
                            print("Telegram alert FAILED")

        # ----- HTTP HANDLER -----
        try:
            cl, remote = s.accept()
        except:
            continue

        try:
            req = cl.recv(1024)
            parts = req.decode().split(" ")
            path = parts[1] if len(parts) > 1 else "/"

            print("HTTP request:", path)

            body = route(path)

            if "<html>" in body:
                header = "HTTP/1.1 200 OK\r\nContent-Type: text/html\r\n\r\n"
            else:
                header = "HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n"

            cl.send(header + body)

        except Exception as e:
            print("HTTP error:", e)

        finally:
            cl.close()

# ----- MAIN -----
def main():
    set_pump(False)
    
    try:
        ip = wifi_connect(WIFI_SSID, WIFI_PASSWORD)
        last_status["ip"] = ip
        send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, "🚀 Plant Monitor Started\nIP: {}".format(ip))
    except Exception as e:
        print("WiFi error:", e)
        return

    start_server(ip)

if __name__ == "__main__":
    main()
