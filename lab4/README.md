# ESP32 → BMP280 Sensor → MQTT → Node-RED → InfluxDB → Grafana Dashboard

## Overview

This project demonstrates an IoT data pipeline using an **ESP32** running **MicroPython**, which collects live environmental data from a **BMP280 sensor**. The ESP32 sends **Pressure**, **Temperature**, and **Altitude** readings to **Node-RED** via **MQTT**, stores them in **InfluxDB**, and visualizes them in **Grafana** dashboards. It highlights how IoT devices can send live data to the cloud for **real-time visualization** and **analysis**.

---

## Equipment

- ESP32 board (MicroPython compatible)
- BMP280 Sensor (Pressure, Temperature, Altitude)
- Laptop or PC with:
  - Node-RED  
  - InfluxDB 1.x  
  - Grafana  
  - MQTT Explorer  
- Wi-Fi connection
- USB cable

---

## Wiring Diagram

**BMP280 Sensor → ESP32**
- VCC → 3.3V  
- GND → GND  
- SDA → GPIO21  
- SCL → GPIO22  

This wiring enables I²C communication between the ESP32 and BMP280 sensor.

---

## Setup Instructions

### Step 1 — ESP32 (MicroPython)
1. Flash ESP32 with **MicroPython firmware**.
2. Use **Thonny IDE** to upload the following files:
   - `main.py`
   - `bmp280.py` (uplaod to micropython)
3. Update Wi-Fi credentials and MQTT topic:
   ```python
   SSID = "YourWiFiName"
   PASSWORD = "YourWiFiPassword"
   BROKER = "test.mosquitto.org"
   TOPIC = b"/aupp/esp32/bmp"
   ```
4. The ESP32 will connect to Wi-Fi, read sensor data, and publish values every 5 seconds.

Example MQTT output:
```
Pressure: 1006 hPa
Temperature: 26.5 °C
Altitude: 64.4 m
```

---

### Step 2 — Node-RED Setup
1. Start Node-RED:
   ```bash
   node-red
   ```
   Open [http://localhost:1880](http://localhost:1880).
2. Add these nodes:
   - **mqtt in**
   - **function**
   - **influxdb out**
   - **debug**
3. Configure **mqtt in**:
   - Server: `test.mosquitto.org`
   - Topic: `/aupp/esp32/bmp`
4. In the **function** node, use the following script to split and format the payload:
   ```javascript
   var data = JSON.parse(msg.payload);
   msg.measurement = "bmp280";
   msg.payload = {
       pressure: data.pressure,
       temperature: data.temperature,
       altitude: data.altitude
   };
   return msg;
   ```
5. Connect all nodes → Deploy → Check live data in Debug window.

---

### Step 3 — InfluxDB Setup
1. Start InfluxDB service:
   ```powershell
   cd "C:\Program Files\InfluxData\influxdb"
   .\influxd.exe
   ```
2. Open a new PowerShell window:
   ```powershell
   cd "C:\Program Files\InfluxData\influxdb"
   .\influx.exe -host 127.0.0.1
   ```
3. Create database and switch to it:
   ```sql
   CREATE DATABASE bmp_lab;
   USE bmp_lab;
   ```
4. Configure **Node-RED InfluxDB out** node:
   - Database: `bmp_lab`
   - Measurement: `bmp280`
   - Fields: `pressure`, `temperature`, `altitude`
5. Run a quick check:
   ```sql
   SELECT * FROM bmp280 ORDER BY time DESC LIMIT 5;
   ```

---

### Step 4 — Grafana Setup
1. Open Grafana: [http://localhost:3000](http://localhost:3000)
2. Login (Default: admin / admin)
3. Add Data Source → **InfluxDB**
   - URL: `http://127.0.0.1:8086`
   - Database: `bmp_lab`
   - Query Language: `InfluxQL`
4. Create a dashboard with **three panels**:
   - **Pressure (Gauge)**
   - **Temperature (Stat)**  
   - **Altitude (Bar)**

### Example Dashboard
![Grafana BMP Dashboard](Screenshot_2025-11-08_at_6.16.06_PM.png)

Each panel updates every 5 seconds as the ESP32 publishes new readings.

---

## Usage Instructions

1. Power on ESP32 → Connects to Wi-Fi.
2. Monitor MQTT data in Node-RED Debug tab.
3. Verify InfluxDB stores values.
4. Open Grafana → View real-time charts for pressure, temperature, and altitude.

---

## Output and Demonstration

| Metric | Example Value | Unit |
|--------|----------------|------|
| Pressure | 1006 | hPa |
| Temperature | 26.5 | °C |
| Altitude | 64.4 | m |

---

## Conclusion

This project extends the previous random-value MQTT lab by integrating a **real sensor (BMP280)** for live environmental data acquisition.  
It demonstrates the complete IoT data flow — **sensing → transmitting → storing → visualizing** — in a scalable and modular pipeline using **MQTT**, **Node-RED**, **InfluxDB**, and **Grafana**.
