# 🚗 Smart Parking Car System 

## 🧭 Overview

This project implements a **three-slot smart parking system** using an **ESP32 microcontroller**.
The system automates car detection, slot allocation, fee calculation, and status monitoring through an **LCD display, web dashboard, and Telegram notifications**.

### ✨ Key Features

* Detects incoming cars using an **ultrasonic sensor** at the entry gate.
* Displays available slots on a **16×2 LCD** screen.
* Automatically opens the **servo gate** if a slot is available.
* Assigns **unique IDs (1–3)** to parked cars in the order they arrive.
* Tracks **time-in and time-out** to calculate parking fees.
* Displays live status on a **web dashboard hosted by the ESP32**.
* Sends **receipts to Telegram** when a car exits.

---

## ⚙️ Functional Requirements

### 🅰️ Entry & Gate Logic

* The **ultrasonic sensor** detects vehicles approaching the gate.
* If all 3 slots are occupied:

  * The **LCD displays “FULL”**.
  * The **gate remains closed**.
* If any slot is free:

  * The LCD shows available slots (e.g., `Free: S1 S3`).
  * The **servo gate opens** automatically.
* The **gate closes** after the car passes or after a short timeout.

---

### 🅱️ Auto-ID Assignment

* System supports **exactly 3 unique IDs (1, 2, 3)**.
* When a car fully parks (IR sensor detects “OCCUPIED” after debounce):

  * The **lowest available ID** is assigned automatically.
  * Records the **time-in** and binds `{ID ↔ Slot}`.
* Each slot tracks:

  * `occupied` (boolean)
  * `assigned_id`
  * `time_in`

---

### 🅲️ Exit & Billing

* When an **IR sensor** for a slot reads “FREE” continuously for ≥ 1 second:

  * The system treats it as a **car exit**.
* It then:

  * Records **time-out**
  * Computes **duration and fee**
  * Marks the ticket as **CLOSED**
  * Frees up the slot and ID

💰 **Pricing rule:**
`1 minute = $0.50`

---

### 🅳️ LCD Display Messages

| System State           | LCD Output       |
| ---------------------- | ---------------- |
| Idle (with free slots) | `Free: S1 S2 S3` |
| All slots occupied     | `FULL`           |

---

### 🅴️ Web Dashboard (ESP32 Hosted)

The ESP32 hosts a live dashboard showing real-time status:

#### Top Status Bar

* **Total:** 3
* **Free:** X
* **Occupied:** Y
* **Status:** Available / FULL

#### Slot Panel (S1–S3)

For each slot:

* Show `Free` or `Occupied`
* If occupied, display:

  * **ID**
  * **Time-In**
  * **Elapsed Time**

#### Ticket Tables

**Active (OPEN) Tickets**

| ID | Slot | Time-In | Elapsed |
| -- | ---- | ------- | ------- |

**Recent (CLOSED) Tickets**

| ID | Slot | Duration | Fee | Time-Out |
| -- | ---- | -------- | --- | -------- |

Dashboard auto-refreshes every **2–5 seconds**.

---

### 🅵️ Telegram Notifications

On each car exit, the ESP32 sends a **Telegram message** containing a digital receipt:

```
✅ Ticket CLOSED
ID: 1
Slot: S2
Duration: 5 minutes
Fee: $2.5
```

---

## 🧩 Hardware Components

* ESP32 microcontroller
* 1 × Ultrasonic sensor (for gate detection)
* 3 × IR sensors (for slot detection)
* 1 × Servo motor (for gate control)
* 1 × 16×2 LCD display
* Jumper wires, breadboard, and power source

---

## 🧠 Future Enhancements

* Add **real-time cloud logging** (Google Sheets or Firebase).
* Support **mobile app integration**.
* Implement **QR-based ticket scanning**.
* Extend for **more than 3 parking slots**.


