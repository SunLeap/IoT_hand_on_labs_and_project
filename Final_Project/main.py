# main.py -- Smart Plant Monitor (MicroPython)
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

TELEGRAM_TOKEN   = "8440902228:AAHEXOESW0EMi6FyvvU23UaTdV1tmpF1LFk"
TELEGRAM_CHAT_ID = "906892123"

DHT_PIN      = 4
SOIL_ADC_PIN = 33
RELAY_PIN    = 17

SOIL_DRY_THRESHOLD = 2500
SENSOR_INTERVAL_MS  = 5000
TELEGRAM_MIN_INTERVAL_S = 60
HTTP_LISTEN_PORT = 80

# ----- GLOBALS -----
sta_if = network.WLAN(network.STA_IF)
dht_sensor = dht.DHT22(machine.Pin(DHT_PIN))

soil_adc = ADC(Pin(SOIL_ADC_PIN))
soil_adc.atten(ADC.ATTN_11DB)
soil_adc.width(ADC.WIDTH_12BIT)

relay = Pin(RELAY_PIN, Pin.OUT)
relay.value(0)  # pump OFF initially

CONTROL_MODE = "AUTO"  # AUTO or MANUAL

last_status = {
    "moisture": None,
    "Moisture": None,
    "temp": None,
    "Temperature": None,
    "humidity": None,
    "Humidity": None,
    "pump": False,
    "Pump": "OFF",
    "mode": CONTROL_MODE,
    "Mode": CONTROL_MODE,
    "ip": None
}

_last_alert_time = 0


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
        return False
    try:
        url = "https://api.telegram.org/bot{}/sendMessage".format(token)
        data = {"chat_id": str(chat_id), "text": text}
        r = requests.post(url, json=data)
        ok = r.status_code == 200
        r.close()
        return ok
    except Exception as e:
        print("Telegram error:", e)
        return False


# ----- PUMP -----
def set_pump(on):
    relay.value(1 if on else 0)
    last_status["pump"] = bool(on)
    last_status["Pump"] = "ON" if on else "OFF"
    print("Pump =", "ON" if on else "OFF")


# ----- HTTP HEADERS -----
HEAD_OK_JSON = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: application/json\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\n"
)

HEAD_OK_HTML = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/html\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\n"
)

HEAD_404 = (
    "HTTP/1.1 404 Not Found\r\n"
    "Content-Type: text/plain\r\n"
    "Access-Control-Allow-Origin: *\r\n"
    "Connection: close\r\n\r\nNot Found"
)


# ----- ROUTING -----
def route(path):
    # Manual pump control
    if path.startswith("/pump/on"):
        set_pump(True)
        return HEAD_OK_JSON + json.dumps(last_status)
    
    if path.startswith("/pump/off"):
        set_pump(False)
        return HEAD_OK_JSON + json.dumps(last_status)
    
    # Mode control
    if path.startswith("/mode/auto"):
        global CONTROL_MODE
        CONTROL_MODE = "AUTO"
        last_status["mode"] = "AUTO"
        last_status["Mode"] = "AUTO"
        return HEAD_OK_JSON + json.dumps(last_status)
    
    if path.startswith("/mode/manual"):
        CONTROL_MODE = "MANUAL"
        last_status["mode"] = "MANUAL"
        last_status["Mode"] = "MANUAL"
        return HEAD_OK_JSON + json.dumps(last_status)
    
    # Status endpoint
    if path.startswith("/status"):
        return HEAD_OK_JSON + json.dumps(last_status)
    
    # Home page
    if path == "/" or path.startswith("/index"):
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Smart Plant Monitor</title>
    <style>
        body {{ font-family: Arial; padding: 20px; background: #f5f5f5; }}
        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h2 {{ color: #2c3e50; margin-top: 0; }}
        .status {{ background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 15px 0; }}
        .status p {{ margin: 8px 0; }}
        .controls {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }}
        button {{ padding: 12px; font-size: 16px; border: none; border-radius: 5px; cursor: pointer; background: #3498db; color: white; }}
        button:hover {{ background: #2980b9; }}
        .btn-danger {{ background: #e74c3c; }}
        .btn-danger:hover {{ background: #c0392b; }}
        .btn-success {{ background: #27ae60; }}
        .btn-success:hover {{ background: #229954; }}
        .full-width {{ grid-column: 1 / -1; }}
    </style>
</head>
<body>
    <div class="container">
        <h2>🌱 Smart Plant Monitor</h2>
        <div class="status">
            <p><strong>IP Address:</strong> {}</p>
            <p><strong>Moisture:</strong> {}</p>
            <p><strong>Temperature:</strong> {}°C</p>
            <p><strong>Humidity:</strong> {}%</p>
            <p><strong>Pump Status:</strong> {}</p>
            <p><strong>Control Mode:</strong> {}</p>
        </div>
        <div class="controls">
            <button class="btn-success" onclick="fetch('/pump/on').then(()=>location.reload())">💧 Pump ON</button>
            <button class="btn-danger" onclick="fetch('/pump/off').then(()=>location.reload())">🛑 Pump OFF</button>
            <button onclick="fetch('/mode/auto').then(()=>location.reload())">🤖 Auto Mode</button>
            <button onclick="fetch('/mode/manual').then(()=>location.reload())">✋ Manual Mode</button>
            <button class="full-width" onclick="location.reload()">🔄 Refresh</button>
        </div>
    </div>
</body>
</html>""".format(
            last_status["ip"],
            last_status["moisture"],
            last_status["temp"],
            last_status["humidity"],
            last_status["Pump"],
            last_status["mode"]
        )
        return HEAD_OK_HTML + html
    
    # Favicon
    if path.startswith("/favicon.ico"):
        return HEAD_OK_HTML
    
    return HEAD_404


# ----- SERVER -----
def start_server(ip):
    global _last_alert_time, CONTROL_MODE
    
    addr = socket.getaddrinfo(ip, HTTP_LISTEN_PORT)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    print("Server started at: http://{}/".format(ip))
    
    last_read = 0
    
    while True:
        # Handle HTTP requests
        try:
            cl, remote = s.accept()
            cl.settimeout(2)
            
            try:
                req = cl.recv(1024)
                if not req:
                    cl.close()
                    continue
                
                try:
                    text = req.decode("utf-8", "ignore")
                except:
                    text = str(req)
                
                # Parse request
                first = ""
                for ln in text.split("\r\n"):
                    if ln:
                        first = ln
                        break
                
                parts = first.split(" ")
                path = parts[1] if len(parts) >= 2 else "/"
                print("HTTP:", path)
                
                # Route and respond
                resp = route(path)
                cl.sendall(resp)
                
            except OSError as e:
                # errno 116 (ETIMEDOUT) is common on mobile; ignore
                if getattr(e, "errno", None) != 116:
                    print("Socket error:", e)
            except Exception as e:
                print("Handler error:", e)
            finally:
                try:
                    cl.close()
                except:
                    pass
                    
        except Exception as e:
            print("Accept error:", e)
            time.sleep(0.1)
        
        # Read sensors periodically
        if time.ticks_diff(time.ticks_ms(), last_read) > SENSOR_INTERVAL_MS:
            last_read = time.ticks_ms()
            
            soil, temp, hum = read_sensors()
            last_status["moisture"] = soil
            last_status["Moisture"] = soil
            last_status["temp"] = temp
            last_status["Temperature"] = temp
            last_status["humidity"] = hum
            last_status["Humidity"] = hum
            
            print("Sensors:", soil, temp, hum)
            
            # Auto mode logic
            if CONTROL_MODE == "AUTO":
                now = time.time()
                
                # Soil dry → pump ON
                if soil >= SOIL_DRY_THRESHOLD and not last_status["pump"]:
                    set_pump(True)
                    if now - _last_alert_time > TELEGRAM_MIN_INTERVAL_S:
                        msg = "🌱 Soil dry → Pump ON\nMoisture={} Temp={}°C Humidity={}%".format(
                            soil, temp, hum
                        )
                        if send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg):
                            _last_alert_time = now
                
                # Soil wet → pump OFF
                elif soil < SOIL_DRY_THRESHOLD and last_status["pump"]:
                    set_pump(False)
                    if now - _last_alert_time > TELEGRAM_MIN_INTERVAL_S:
                        msg = "💧 Soil wet → Pump OFF\nMoisture={} Temp={}°C Humidity={}%".format(
                            soil, temp, hum
                        )
                        if send_telegram_message(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID, msg):
                            _last_alert_time = now


# ----- MAIN -----
def main():
    global _last_alert_time
    
    # Initialize
    set_pump(False)
    
    # Connect WiFi
    try:
        ip = wifi_connect(WIFI_SSID, WIFI_PASSWORD)
        last_status["ip"] = ip
    except Exception as e:
        print("WiFi error:", e)
        last_status["ip"] = None
        return
    
    # Start server
    start_server(ip)


if __name__ == "__main__":
    main()