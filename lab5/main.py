import network, socket, ure, time, json
from machine import Pin, PWM
from umqtt.simple import MQTTClient

# --- Wi-Fi ---
WIFI_SSID = "sLEAP"
WIFI_PASS = "33339999"

# --- MQTT ---
MQTT_BROKER = "172.20.10.2"
MQTT_PORT = 1883
MQTT_TOPIC = "lab5/motor/logs"   
MQTT_CLIENT_ID = "esp32_motor_" + str(time.ticks_ms())

mqtt_client = None

def wifi_connect():
    sta = network.WLAN(network.STA_IF)

    # Reset Wi-Fi hardware
    sta.active(False)
    time.sleep(1)
    sta.active(True)

    print("Connecting to WiFi...")

    sta.connect(WIFI_SSID, WIFI_PASS)

    for _ in range(80):
        if sta.isconnected():
            print("Connected:", sta.ifconfig())
            return sta.ifconfig()[0]
        time.sleep(0.25)

    raise RuntimeError("WiFi connect failed")


def mqtt_connect():
    global mqtt_client
    try:
        mqtt_client = MQTTClient(MQTT_CLIENT_ID, MQTT_BROKER, MQTT_PORT)
        mqtt_client.connect()
        print("MQTT connected to", MQTT_BROKER)
    except Exception as e:
        print("MQTT connect failed:", e)
        mqtt_client = None

def mqtt_publish(action, speed):
    if mqtt_client is None:
        return
    try:
        timestamp = time.time()
        
        # Convert speed to signed value for plotting
        if action == "forward":
            speed_signed = speed
        elif action == "backward":
            speed_signed = -speed
        else:  # stop
            speed_signed = 0

        # Build payload
        payload = {
            "timestamp": timestamp,
            "action": action,
            "speed": speed,
            "speed_signed": speed_signed
        }

        # Publish to MQTT
        mqtt_client.publish(MQTT_TOPIC, json.dumps(payload))
        print("MQTT published:", payload)

    except Exception as e:
        print("MQTT publish failed:", e)
        
# --- L298N pins ---
IN1 = Pin(26, Pin.OUT)
IN2 = Pin(27, Pin.OUT)
ENA = PWM(Pin(25), freq=1000)
PWM_MAX = 1023
_speed_pct = 70

def set_speed(pct):
    global _speed_pct
    pct = int(max(0, min(100, pct)))
    _speed_pct = pct
    ENA.duty(int(PWM_MAX * (_speed_pct / 100.0)))
    print("Speed:", _speed_pct, "%")
    mqtt_publish("speed_change", _speed_pct)

def motor_forward():
    set_speed(_speed_pct)
    IN1.on()
    IN2.off()
    print("Forward")
    mqtt_publish("forward", _speed_pct)

def motor_backward():
    set_speed(_speed_pct)
    IN1.off()
    IN2.on()
    print("Backward")
    mqtt_publish("backward", _speed_pct)

def motor_stop():
    IN1.off()
    IN2.off()
    ENA.duty(0)
    print("Stop")
    mqtt_publish("stop", 0)

# --- HTTP ---
HEAD_OK_TEXT = (
    "HTTP/1.1 200 OK\r\n"
    "Content-Type: text/plain\r\n"
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

HOME_HTML = """<!doctype html><meta name=viewport content="width=device-width,initial-scale=1">
<h3>ESP32 Motor with MQTT</h3>
<p>
  <a href="/forward"><button>Forward</button></a>
  <a href="/backward"><button>Backward</button></a>
  <a href="/stop"><button>Stop</button></a>
</p>
<p>
  <label>Speed:</label>
  <input id="spd" type="range" min="0" max="100" value="70"
    oninput="fetch('/speed?value='+this.value).then(r=>r.text()).then(console.log);">
</p>
<p><small>Data published to MQTT: aupp/esp32/random</small></p>
"""

def route(path):
    if path == "/" or path.startswith("/index"):
        return HEAD_OK_HTML + HOME_HTML
    if path.startswith("/favicon.ico"):
        return HEAD_OK_TEXT
    if path.startswith("/forward"):
        motor_forward()
        return HEAD_OK_TEXT + "forward"
    if path.startswith("/backward"):
        motor_backward()
        return HEAD_OK_TEXT + "backward"
    if path.startswith("/stop"):
        motor_stop()
        return HEAD_OK_TEXT + "stop"
    if path.startswith("/speed"):
        m = ure.search(r"value=(\d+)", path)
        if m:
            set_speed(int(m.group(1)))
            return HEAD_OK_TEXT + "speed=" + m.group(1)
        return HEAD_OK_TEXT + "speed?value=0..100"
    print("Unknown path:", path)
    return HEAD_404

def start_server(ip):
    addr = socket.getaddrinfo(ip, 80)[0][-1]
    s = socket.socket()
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(addr)
    s.listen(3)
    print("HTTP:", "http://%s/" % ip)

    while True:
        try:
            cl, _ = s.accept()
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

                first = ""
                for ln in text.split("\r\n"):
                    if ln:
                        first = ln
                        break
                parts = first.split(" ")
                path = parts[1] if len(parts) >= 2 else "/"

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

# --- main ---
if __name__ == "__main__":
    motor_stop()
    set_speed(_speed_pct)
    ip = wifi_connect()
    mqtt_connect()
    start_server(ip)