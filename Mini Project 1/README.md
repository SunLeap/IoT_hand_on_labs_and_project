# ESP32 Smart Parking System

This project implements a three-slot smart parking system using an ESP32 microcontroller. It automates the entire parking process, from gate entry and slot assignment to billing and real-time monitoring via a web dashboard and Telegram notifications.

## 1. Overview

The system is designed to manage a small parking lot with three spaces. It uses an ultrasonic sensor to detect vehicles at the entrance, IR sensors to monitor each parking slot, and a servo motor to operate the entry gate. The ESP32 hosts a web server that displays a live dashboard of the parking status and sends automated receipts to a Telegram chat upon a vehicle's departure.

## 2. Features

-   **Automatic Gate Control:** An ultrasonic sensor detects arriving vehicles. The servo-controlled gate opens only if a parking slot is available.
-   **Dynamic ID Assignment:** Cars are automatically assigned the lowest available ID (1, 2, or 3) when they occupy a slot. No manual input is required.
-   **Automated Time & Billing:** The system automatically records the time-in and time-out for each vehicle and calculates the parking fee based on the duration.
-   **Live Web Dashboard:** The ESP32 hosts a web page, accessible on the local network, showing:
    -   Overall parking status (Total, Free, Occupied).
    -   Live status of each individual slot (Free/Occupied, ID, Elapsed Time).
    -   Tables for active (OPEN) and recent (CLOSED) parking tickets.
-   **Telegram Notifications:** A detailed receipt is automatically sent to a specified Telegram chat when a car leaves and the ticket is closed.
-   **LCD Display:** A 16x2 I2C LCD provides on-site, at-a-glance information about available slots or indicates if the lot is full.

## 3. Hardware Requirements

| Component                     | Quantity |
| ----------------------------- | :------: |
| ESP32 Development Board       |    1     |
| HC-SR04 Ultrasonic Sensor     |    1     |
| IR Obstacle Avoidance Sensor  |    3     |
| SG90 Servo Motor              |    1     |
| 16x2 I2C LCD Display          |    1     |
| Breadboard                    |    1     |
| Jumper Wires                  |   Set    |
| 5V Power Supply               |    1     |

## 4. Wiring Diagram

Connect the components to the ESP32 GPIO pins as defined in the code:

| Component              | ESP32 Pin  |
| ---------------------- | :--------: |
| **Ultrasonic Sensor** |            |
| `TRIG`                 |  `GPIO 27` |
| `ECHO`                 |  `GPIO 26` |
| **IR Sensors** |            |
| `IR Sensor (Slot 1)`   |  `GPIO 23` |
| `IR Sensor (Slot 2)`   |  `GPIO 34` |
| `IR Sensor (Slot 3)`   |  `GPIO 19` |
| **Servo Motor** |            |
| `Signal Pin`           |  `GPIO 14` |
| **I2C LCD Display** |            |
| `SDA`                  |  `GPIO 21` |
| `SCL`                  |  `GPIO 22` |

**Note:** Ensure all components are connected to a common ground (GND) and that the Servo and LCD are powered by a stable 5V source.

## 5. Software & Setup

### Prerequisites

1.  **MicroPython Firmware:** Your ESP32 must be flashed with the latest version of MicroPython.
2.  **IDE:** An IDE for MicroPython development, such as [Thonny](https://thonny.org/), is recommended for easy file management and code execution.

### Installation Steps

1.  **Download Library:** This project requires the `machine_i2c_lcd.py` library. You can find a standard version of this library online. Download the file.
2.  **Upload Files to ESP32:**
    -   Connect your ESP32 to your computer and open Thonny.
    -   Upload the `machine_i2c_lcd.py` library to the root directory of your ESP32.
    -   Copy the main project code and save it as `main.py`.
    -   Upload `main.py` to the root directory of your ESP32.

3.  **Configure Credentials:**
    Open the `main.py` file and update the following configuration variables with your own details:

    ```python
    # WiFi Credentials
    WIFI_SSID = 'Your_WiFi_Name'
    WIFI_PASSWORD = 'Your_WiFi_Password'

    # Telegram Bot Details
    TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
    TELEGRAM_CHAT_ID = YOUR_NUMERIC_CHAT_ID
    ```

4.  **Run the System:**
    -   Reboot your ESP32. The `main.py` script will run automatically.
    -   The LCD will display the ESP32's IP address upon connecting to WiFi.

## 6. How to Use

1.  **Power On:** Power the ESP32 and connected components.
2.  **Entry:** A car approaches the gate. If space is available, the gate opens.
3.  **Parking:** The car parks, and an ID is assigned. The web dashboard and LCD update.
4.  **Monitoring:** View the live status on the web dashboard by navigating to the ESP32's IP address.
5.  **Exit:** The car leaves, the system calculates the fee, and a receipt is sent to Telegram. The slot becomes free.
