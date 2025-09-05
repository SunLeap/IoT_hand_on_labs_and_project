# IoT Temperature Sensor with Relay Control (Telegram Bot)

## Project Overview
In this lab, I built a small IoT monitoring system using an **ESP32**, a **DHT22 sensor**, and a **relay module**.  
The ESP32 constantly monitors temperature and humidity, and when things heat up (above 30 °C), it alerts me on **Telegram**.  

From Telegram, I can:
- Check the current temperature, humidity, and relay status.
- Turn the relay **on** or **off** with simple chat commands.
- Get an automatic **“auto-OFF”** message when the temperature cools down.

This project combines **sensing, actuation, and networking** with a real-world control interface via Telegram.

---

## What I Learned
- How to design and implement an **ESP32 + MicroPython IoT system**.  
- Writing simple **state machines** for sensor sampling and relay logic.  
- Using the **Telegram Bot API** for chat-based control.  
- Making the system more robust (auto-reconnect Wi-Fi, handle errors, avoid crashes).  
- Thinking about **performance** (sampling every 5s) and **safety** (relay load & isolation).  

---

## What You’ll Need
- ESP32 Dev Board (flashed with MicroPython)  
- DHT22 temperature & humidity sensor  
- Relay module  
- Jumper wires  
- USB cable + laptop with Thonny IDE  
- Wi-Fi connection  

---

## Wiring Setup
**ESP32 → DHT22 + Relay connections:**

| ESP32 Pin | Component | Purpose |
|-----------|-----------|---------|
| 3V3       | DHT22 VCC | Power for sensor |
| GND       | DHT22 GND | Ground |
| GPIO4     | DHT22 Data| Temperature & humidity data |
| GPIO2     | Relay IN  | Relay control input |
| 3V3       | Relay VCC | Power for relay |
| GND       | Relay GND | Ground |


---

## Setup & Configuration
1. Flash your ESP32 with **MicroPython**.  
2. Clone this repository and open it in **Thonny**.  
3. Edit `main.py` with your Wi-Fi and bot details:
   ```python
   WIFI_SSID     = "YourWiFiName"
   WIFI_PASSWORD = "YourWiFiPassword"

   BOT_TOKEN     = "Your_Telegram_Bot_Token"
   ALLOWED_CHAT_IDS = {123456789}  # Replace with your chat/group ID
