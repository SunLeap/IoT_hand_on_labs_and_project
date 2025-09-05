import network, time, urequests, json
from machine import Pin, reset
import dht

WIFI_SSID = "V"
WIFI_PASSWORD = "12345678"
BOT_TOKEN = "8254366823:AAGObjQr_ysNBtt5c6JW7a7OIE8wbMuUSlU"
ALLOWED_CHAT_IDS = {-4908400638}  

RELAY_PIN = 2
RELAY_ACTIVE_LOW = False
POLL_TIMEOUT_S = 25
DEBUG = True
DHT_PIN = 4
ALERT_TEMP = 30.0

API = "https://api.telegram.org/bot" + BOT_TOKEN
relay = Pin(RELAY_PIN, Pin.OUT)
sensor = dht.DHT22(Pin(DHT_PIN))
alert_active = False
last_alert_time = 0

def log(*a):
    if DEBUG:
        print(*a)

def _urlencode(d):
    p = []
    for k, v in d.items():
        s = str(v)
        s = s.replace("%", "%25").replace(" ", "%20").replace("\n", "%0A")
        s = s.replace("&", "%26").replace("?", "%3F").replace("=", "%3D")
        p.append(str(k) + "=" + s)
    return "&".join(p)

def relay_on(): relay.value(0 if RELAY_ACTIVE_LOW else 1)
def relay_off(): relay.value(1 if RELAY_ACTIVE_LOW else 0)
def relay_is_on(): return (relay.value() == 0) if RELAY_ACTIVE_LOW else (relay.value() == 1)

def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        t0 = time.time()
        while not wlan.isconnected():
            if time.time() - t0 > 25:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.25)
    log("Wi-Fi OK:", network.WLAN(network.STA_IF).ifconfig())
    return wlan

def ensure_wifi():
    wlan = network.WLAN(network.STA_IF)
    if wlan.isconnected():
        return True
    try:
        wlan.active(False)
        time.sleep(0.2)
        wlan.active(True)
        wlan.connect(WIFI_SSID, WIFI_PASSWORD)
        t0 = time.time()
        while not wlan.isconnected():
            if time.time() - t0 > 10:
                break
            time.sleep(0.25)
    except:
        return False
    return wlan.isconnected()

def send_message(chat_id, text):
    try:
        url = API + "/sendMessage?" + _urlencode({"chat_id": chat_id, "text": text})
        r = urequests.get(url)
        sc = getattr(r, "status_code", 0)
        _ = r.text
        r.close()
        if sc != 200:
            print("send_message HTTP", sc)
            return False
        return True
    except Exception as e:
        print("send_message error:", e)
        return False

def get_updates(offset=None, timeout=POLL_TIMEOUT_S):
    qs = {"timeout": timeout}
    if offset is not None:
        qs["offset"] = offset
    url = API + "/getUpdates?" + _urlencode(qs)
    try:
        r = urequests.get(url)
        sc = getattr(r, "status_code", 0)
        if sc != 200:
            print("get_updates HTTP", sc)
            try:
                _ = r.text
            except:
                pass
            r.close()
            return []
        data = r.json()
        r.close()
        if not data.get("ok"):
            print("getUpdates not ok:", data)
            return []
        return data.get("result", [])
    except Exception as e:
        print("get_updates error:", e)
        return []

def handle_cmd(chat_id, text):
    global alert_active, last_alert_time
    t = (text or "").strip().lower()
    if t in ("/on", "on"):
        relay_on()
        alert_active = False
        last_alert_time = 0
        send_message(chat_id, "Relay: ON")
    elif t in ("/off", "off"):
        relay_off()
        send_message(chat_id, "Relay: OFF")
    elif t in ("/status", "status"):
        try:
            for _ in range(3):
                try:
                    time.sleep(0.5)
                    sensor.measure()
                    temp = sensor.temperature()
                    hum = sensor.humidity()
                    break
                except OSError:
                    temp = None
                    hum = None
            if temp is None:
                send_message(chat_id, "Sensor error: read failed")
                return
            rs = "ON" if relay_is_on() else "OFF"
            send_message(chat_id, "Temp: {:.2f}°C\nHumidity: {:.2f}%\nRelay: {}".format(temp, hum, rs))
        except Exception as e:
            send_message(chat_id, "Sensor error: {}".format(e))
    elif t in ("/start", "/help", "help"):
        send_message(chat_id, "Commands:\n/on\n/off\n/status")
    else:
        send_message(chat_id, "Unknown. Try /on, /off, /status")

def main():
    global ALLOWED_CHAT_IDS, alert_active, last_alert_time
    try:
        connect_wifi()
    except:
        pass
    relay_off()
    last_id = None
    old = get_updates(timeout=1)
    if old:
        last_id = old[-1]["update_id"]
    while True:
        if not ensure_wifi():
            time.sleep(1)
            continue
        updates = get_updates(offset=(last_id + 1) if last_id is not None else None)
        for u in updates:
            last_id = u.get("update_id", last_id)
            msg = u.get("message") or u.get("edited_message")
            if not msg:
                continue
            chat_id = msg["chat"]["id"]
            text = msg.get("text", "")
            if not ALLOWED_CHAT_IDS:
                ALLOWED_CHAT_IDS = {chat_id}
                send_message(chat_id, "Authorized.")
            if chat_id not in ALLOWED_CHAT_IDS:
                send_message(chat_id, "Not authorized.")
                continue
            handle_cmd(chat_id, text)
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum = sensor.humidity()
        except OSError:
            time.sleep(1)
            continue
        except Exception:
            time.sleep(1)
            continue
        if temp >= ALERT_TEMP and not relay_is_on():
            now = time.time()
            if not alert_active:
                alert_active = True
                last_alert_time = 0
            if now - last_alert_time >= 5:
                for cid in ALLOWED_CHAT_IDS:
                    send_message(cid, "Alert! Temp: {:.2f}°C, Humidity: {:.2f}%, Relay is OFF".format(temp, hum))
                last_alert_time = now
            time.sleep(0.2)
            continue
        if temp < ALERT_TEMP and relay_is_on():
            relay_off()
            alert_active = False
            last_alert_time = 0
            for cid in ALLOWED_CHAT_IDS:
                send_message(cid, "Temp dropped to {:.2f}°C → relay auto-OFF".format(temp))
        time.sleep(1)

try:
    main()
except Exception as e:
    print("Fatal error:", e)
    time.sleep(5)
    reset()
