import network, time
from umqtt.simple import MQTTClient
from machine import Pin, I2C
from bmp280 import BMP280

# ==== WiFi & MQTT Config ====
SSID = "..."
PASSWORD = "#12345687"

BROKER = "test.mosquitto.org"
PORT = 1883
CLIENT_ID = b"esp32_bmp280_1"
TOPIC = b"/aupp/esp32/ravy"
KEEPALIVE = 30

# ==== Connect to WiFi ====
def wifi_connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi...")
        wlan.connect(SSID, PASSWORD)
        t0 = time.ticks_ms()
        while not wlan.isconnected():
            if time.ticks_diff(time.ticks_ms(), t0) > 20000:
                raise RuntimeError("Wi-Fi connect timeout")
            time.sleep(0.3)
    print("WiFi OK:", wlan.ifconfig())
    return wlan

# ==== MQTT Client ====
def make_client():
    return MQTTClient(client_id=CLIENT_ID, server=BROKER, port=PORT, keepalive=KEEPALIVE)

def connect_mqtt(client):
    time.sleep(0.5)
    client.connect()
    print("MQTT connected")

# ==== BMP280 Setup ====
def setup_bmp280():
    i2c = I2C(0, scl=Pin(22), sda=Pin(21))
    bmp = BMP280(i2c, addr=0x76)
    return bmp

# ==== Main Loop ====
def main():
    wifi_connect()
    client = make_client()
    bmp = setup_bmp280()

    while True:
        try:
            connect_mqtt(client)
            while True:
                # Read sensor data
                temperature = bmp.temperature
                pressure = bmp.pressure / 100  # Convert Pa → hPa
                altitude = bmp.altitude

                # Combine as JSON-like string
                msg = '{{"temperature": {:.2f}, "pressure": {:.2f}, "altitude": {:.2f}}}'.format(
                    temperature, pressure, altitude
                )

                client.publish(TOPIC, msg)
                print("Sent:", msg)
                time.sleep(5)

        except OSError as e:
            print("MQTT error:", e)
            try:
                client.close()
            except:
                pass
            print("Retrying MQTT in 3s...")
            time.sleep(3)

main()