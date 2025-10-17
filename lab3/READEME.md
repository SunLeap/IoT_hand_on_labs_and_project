# IoT Atmospheric Sensor using BMP280 and ESP32

## Project Overview

In this lab, I built a small IoT environmental monitoring system using an **ESP32** and a **BMP280** sensor.  
The BMP280 measures **temperature**, **pressure**, and **altitude**, and the ESP32 reads these values and displays them through the serial monitor. This system can also be expanded to send the sensor data to the cloud or an IoT dashboard in real time. The goal of this project is to understand how sensors communicate with microcontrollers using the **I²C interface**, and how to collect and process environmental data accurately.

---

## What I Learned

- How to interface the **BMP280** sensor with an **ESP32** using MicroPython.  
- How to read **temperature**, **pressure**, and **altitude** data from the sensor.  
- Understanding how the **I²C communication protocol** works.  
- How to use **Thonny IDE** to program and upload code to ESP32.  
- How to calculate **altitude** using pressure data.  
- How this sensor can be applied to real-world IoT applications such as **weather stations** or **drone height tracking**.

---

## What You’ll Need

- ESP32 Dev Board (flashed with MicroPython)  
- BMP280 Sensor Module  
- Jumper Wires  
- USB Cable + Laptop with **Thonny IDE**  
- Wi-Fi connection (optional if extending to IoT cloud logging)

---

## Wiring Setup

ESP32 → BMP280 connections:

| ESP32 Pin | BMP280 Pin | Purpose |
|------------|-------------|----------|
| 3V3 | VCC | Power supply |
| GND | GND | Ground |
| GPIO22 | SCL | I²C clock line |
| GPIO21 | SDA | I²C data line |

---

## Wiring Diagram

*(Insert your wiring image here if available)*  
Example connection:  
`ESP32 GPIO22 → BMP280 SCL`  
`ESP32 GPIO21 → BMP280 SDA`

---

## Setup & Configuration

1. Flash your ESP32 with **MicroPython** firmware.  
2. Open **Thonny IDE** and connect to your ESP32 board.  
3. Upload the `bmp280.py` driver file to your ESP32.  
4. Create and save the following code as `main.py`:


