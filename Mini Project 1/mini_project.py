import machine
from machine import Pin, PWM
import time
import network
import urequests
import utime
import socket
import ujson

#IR Pin
IR_SLOT1 = 23
IR_SLOT2 = 34
IR_SLOT3 = 19

#UltraSonic Pin
ULTRASONIC_TRIG = 27
ULTRASONIC_ECHO = 26

#Servo Pin
SERVO_PIN = 14

LCD_SDA = 21
LCD_SCL = 22

WIFI_SSID = 'Robotic WIFI'
WIFI_PASSWORD = 'rbtWIFI@2025'

# Telegram Bot
TELEGRAM_BOT_TOKEN = "8381403261:AAFIaPvYwwkE_-FHyDpFJDig5ZFM13tTnW4"
TELEGRAM_CHAT_ID =  1236085869
DEBUG = True
API = "https://api.telegram.org/bot" + TELEGRAM_BOT_TOKEN

TOTAL_SLOTS = 3
DETECTION_DISTANCE = 10
DEBOUNCE_TIME = 500
LEAVE_GRACE_TIME = 1000
GATE_OPEN_TIME = 5000
PRICE_PER_MINUTE = 0.5

from machine_i2c_lcd import I2cLcd

def _urlencode(d):
    parts = []
    for k, v in d.items():
        if isinstance(v, int):
            v = str(v)
        s = str(v)
        s = s.replace("%", "%25").replace(" ", "%20").replace("\n", "%0A")
        s = s.replace("&", "%26").replace("?", "%3F").replace("=", "%3D")
        parts.append(str(k) + "=" + s)
    return "&".join(parts)

def log(*args):
    if DEBUG:
        print(*args)
        
class Slot:
    def __init__(self, ir_pin, slot_num):
        self.ir_pin = Pin(ir_pin, Pin.IN, Pin.PULL_UP)
        self.slot_num = slot_num
        self.occupied = False
        self.assigned_id = 0
        self.time_in = 0
        self.last_change_time = 0
        self.pending_exit = False
        self.exit_start_time = 0
        self.last_state = self.ir_pin.value()
    
    def is_detected(self):
        return self.ir_pin.value() == 0
    
    def get_elapsed_seconds(self):
        if self.occupied and self.time_in > 0:
            return (utime.ticks_ms() - self.time_in) // 1000
        return 0
    
    def get_elapsed_str(self):
        seconds = self.get_elapsed_seconds()
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}m {secs}s"

class Ticket:
    def __init__(self, ticket_id, slot, time_in):
        self.id = ticket_id
        self.slot = slot
        self.time_in = time_in
        self.time_out = 0
        self.duration = 0
        self.fee = 0
        self.closed = False


class ParkingSystem:
    def __init__(self):
        # Setup pins
        self.trig = Pin(ULTRASONIC_TRIG, Pin.OUT)
        self.echo = Pin(ULTRASONIC_ECHO, Pin.IN)
        
        # Setup servo
        self.servo = PWM(Pin(SERVO_PIN), freq=50)
        self.close_gate()
        
        # Setup LCD
        i2c = machine.I2C(0, sda=Pin(LCD_SDA), scl=Pin(LCD_SCL), freq=400000)
        self.lcd = I2cLcd(i2c, 0x27, 2, 16)  # i2c, address, rows, cols
        
        # Setup slots
        self.slots = [
            Slot(IR_SLOT1, 1),
            Slot(IR_SLOT2, 2),
            Slot(IR_SLOT3, 3)
        ]
        
        # ID management
        self.used_ids = [False, False, False, False]  # Index 0 unused, 1-3 for IDs
        
        # Gate state
        self.gate_open = False
        self.gate_open_time = 0
        
        # Ticket history
        self.ticket_history = []
        
        # Timing
        self.last_ultrasonic_check = 0
        
        # WiFi
        self.wlan = None
        self.connect_wifi()
        
        # Web server socket
        self.server_socket = None
        self.setup_server()
        
        self.lcd.clear()
        self.lcd.putstr("System Ready")
        time.sleep(2)
        self.update_lcd()
    
    def connect_wifi(self):
        self.wlan = network.WLAN(network.STA_IF)
        self.wlan.active(True)
        
        self.lcd.clear()
        self.lcd.putstr("Connecting WiFi")
        
        if not self.wlan.isconnected():
            self.wlan.connect(WIFI_SSID, WIFI_PASSWORD)
            attempts = 0
            while not self.wlan.isconnected() and attempts < 20:
                time.sleep(0.5)
                attempts += 1
        
        if self.wlan.isconnected():
            print("WiFi Connected!")
            print("IP:", self.wlan.ifconfig()[0])
            self.lcd.clear()
            self.lcd.putstr("WiFi Connected")
            self.lcd.move_to(0, 1)
            self.lcd.putstr(self.wlan.ifconfig()[0])
        else:
            print("WiFi Failed!")
            self.lcd.clear()
            self.lcd.putstr("WiFi Failed!")
        
        time.sleep(2)
    
    def setup_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind(('0.0.0.0', 80))
        self.server_socket.listen(1)
        self.server_socket.setblocking(False)
        print("Web server started on port 80")
    
    def measure_distance(self):
        self.trig.value(0)
        time.sleep_us(2)
        self.trig.value(1)
        time.sleep_us(10)
        self.trig.value(0)
        
        try:
            pulse_time = machine.time_pulse_us(self.echo, 1, 30000)
            if pulse_time > 0:
                distance = (pulse_time * 0.034) / 2
                return distance
        except:
            pass
        return -1
    def set_servo_angle(self, angle):
        """Converts an angle (0-180) to a duty_u16 value and sets the servo."""
        # Ensure the angle is within the valid range
        if not 0 <= angle <= 180:
            print("Error: Angle must be between 0 and 180.")
            return
            
        # These min/max duty values are based on your original code's values.
        # 0 degrees = 4915
        # 90 degrees = 7372
        # We can calculate the range to map any angle.
        min_duty = 4915
        max_duty = 9829 # This is the calculated value for 180 degrees
        
        # Linearly map the angle to the duty cycle range
        duty_u16 = int(min_duty + (angle / 180) * (max_duty - min_duty))
        
        self.servo.duty_u16(duty_u16)
        time.sleep(0.4) # A little delay to allow the servo to move
    
    def open_gate(self):
        self.set_servo_angle(90)  # ~90 degrees
        self.gate_open = True
        self.gate_open_time = utime.ticks_ms()
        print("Gate opened")
    
    def close_gate(self):
        self.set_servo_angle(0)  # 0 degrees
        self.gate_open = False
        print("Gate closed")
    
    def get_free_slot_count(self):
        return sum(1 for slot in self.slots if not slot.occupied)
    
    def get_free_slots_str(self):
        free_slots = [f"S{slot.slot_num}" for slot in self.slots if not slot.occupied]
        return " ".join(free_slots) if free_slots else ""
    
    def update_lcd(self):
        self.lcd.clear()
        free_count = self.get_free_slot_count()
        
        if free_count == 0:
            self.lcd.putstr("FULL")
        else:
            free_str = self.get_free_slots_str()
            self.lcd.putstr("Free: " + free_str[:10])
    
    def get_lowest_available_id(self):
        for i in range(1, 4):
            if not self.used_ids[i]:
                return i
        return 0
    
    def assign_car_to_slot(self, slot):
        car_id = self.get_lowest_available_id()
        if car_id == 0:
            return
        
        slot.occupied = True
        slot.assigned_id = car_id
        slot.time_in = utime.ticks_ms()
        self.used_ids[car_id] = True
        
        print(f"Car assigned: ID={car_id}, Slot=S{slot.slot_num}")
        self.update_lcd()
    
    def process_exit(self, slot):
        if not slot.occupied:
            return
        
        # Create ticket
        ticket = Ticket(slot.assigned_id, slot.slot_num, slot.time_in)
        ticket.time_out = utime.ticks_ms()
        
        # Calculate duration and fee
        duration_ms = ticket.time_out - ticket.time_in
        duration_min = duration_ms / 60000
        ticket.duration = round(duration_min, 2)
        ticket.fee = round(duration_min * PRICE_PER_MINUTE, 2)
        ticket.closed = True
        
        # Add to history
        self.ticket_history.append(ticket)
        if len(self.ticket_history) > 20:
            self.ticket_history.pop(0)
        
        print(f"Car exit: ID={ticket.id}, Slot=S{ticket.slot}, Duration={ticket.duration}min, Fee=${ticket.fee}")
        
        # Send Telegram notification
        self.send_telegram_receipt(ticket)
        
        # Free slot and ID
        self.used_ids[slot.assigned_id] = False
        slot.occupied = False
        slot.assigned_id = 0
        slot.time_in = 0
        
        self.update_lcd()
    
    def send_telegram_message(self, text):
        """Send message via Telegram using working GET method"""
        if not self.wlan.isconnected():
            print("WiFi not connected, cannot send Telegram message.")
            return False
        
        try:
            url = API + "/sendMessage?" + _urlencode({
                "chat_id": TELEGRAM_CHAT_ID,
                "text": text
            })
            
            log(f"Sending to Telegram: {text[:50]}...")
            r = urequests.get(url)
            response_text = r.text
            r.close()
            
            log("Telegram response:", response_text)
            return True
            
        except Exception as e:
            print(f"Telegram error: {e}")
            return False
    
    def send_telegram_receipt(self, ticket):
        """Send parking receipt via Telegram"""
        message = (
            f"✅ Ticket CLOSED\n"
            f"ID: {ticket.id}\n"
            f"Slot: S{ticket.slot}\n"
            f"Duration: {ticket.duration} minutes\n"
            f"Fee: ${ticket.fee}"
        )
        
        success = self.send_telegram_message(message)
        if success:
            print("✓ Telegram receipt sent successfully")
        else:
            print("✗ Failed to send Telegram receipt")
    
    def check_ultrasonic(self):
        current_time = utime.ticks_ms()
        if utime.ticks_diff(current_time, self.last_ultrasonic_check) < 500:
            return
        
        self.last_ultrasonic_check = current_time
        distance = self.measure_distance()
        
        if 0 < distance < DETECTION_DISTANCE and not self.gate_open:
            free_count = self.get_free_slot_count()
            if free_count > 0:
                self.open_gate()
            self.update_lcd()
    
    def check_slots(self):
        for slot in self.slots:
            current_state = slot.is_detected()
            current_time = utime.ticks_ms()
            
            # Debounce
            if current_state != slot.last_state:
                if utime.ticks_diff(current_time, slot.last_change_time) > DEBOUNCE_TIME:
                    
                    # FREE to OCCUPIED
                    if current_state and not slot.occupied:
                        self.assign_car_to_slot(slot)
                        slot.pending_exit = False
                    
                    # OCCUPIED to FREE
                    elif not current_state and slot.occupied:
                        slot.pending_exit = True
                        slot.exit_start_time = current_time
                    
                    slot.last_change_time = current_time
                    slot.last_state = current_state
            
            # Check for confirmed exit
            if slot.pending_exit and not current_state:
                if utime.ticks_diff(current_time, slot.exit_start_time) >= LEAVE_GRACE_TIME:
                    self.process_exit(slot)
                    slot.pending_exit = False
            
            # Cancel pending exit if car returns
            if slot.pending_exit and current_state:
                slot.pending_exit = False
    
    def get_web_page(self):
        free_count = self.get_free_slot_count()
        occupied_count = TOTAL_SLOTS - free_count
        status = "Available" if free_count > 0 else "FULL"
        
        # Build slot panels
        slot_panels = ""
        for slot in self.slots:
            if slot.occupied:
                slot_panels += f"""
                <div class="slot occupied">
                    <h3>Slot S{slot.slot_num}</h3>
                    <p class="status">🚗 Occupied</p>
                    <p>ID: {slot.assigned_id}</p>
                    <p>Elapsed: {slot.get_elapsed_str()}</p>
                </div>
                """
            else:
                slot_panels += f"""
                <div class="slot free">
                    <h3>Slot S{slot.slot_num}</h3>
                    <p class="status">✅ Free</p>
                </div>
                """
        
        # Active tickets
        active_tickets = ""
        for slot in self.slots:
            if slot.occupied:
                active_tickets += f"""
                <tr>
                    <td>{slot.assigned_id}</td>
                    <td>S{slot.slot_num}</td>
                    <td>{time.localtime(slot.time_in//1000)[3]}:{time.localtime(slot.time_in//1000)[4]:02d}</td>
                    <td>{slot.get_elapsed_str()}</td>
                </tr>
                """
        
        if not active_tickets:
            active_tickets = "<tr><td colspan='4'>No active tickets</td></tr>"
        
        # Recent closed tickets
        recent_tickets = ""
        for ticket in reversed(self.ticket_history[-10:]):
            recent_tickets += f"""
            <tr>
                <td>{ticket.id}</td>
                <td>S{ticket.slot}</td>
                <td>{ticket.duration} min</td>
                <td>${ticket.fee}</td>
                <td>{time.localtime(ticket.time_out//1000)[3]}:{time.localtime(ticket.time_out//1000)[4]:02d}</td>
            </tr>
            """
        
        if not recent_tickets:
            recent_tickets = "<tr><td colspan='5'>No recent tickets</td></tr>"
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Smart Parking System</title>
    <meta charset="UTF-8">
    <meta http-equiv="refresh" content="3">
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: Arial, sans-serif; background: #f0f0f0; padding: 20px; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        h1 {{ color: #333; margin-bottom: 20px; text-align: center; }}
        .status-bar {{ background: #2196F3; color: white; padding: 15px; border-radius: 5px; display: flex; justify-content: space-around; margin-bottom: 20px; }}
        .status-item {{ text-align: center; }}
        .status-item h3 {{ font-size: 14px; margin-bottom: 5px; }}
        .status-item p {{ font-size: 24px; font-weight: bold; }}
        .slots {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px; margin-bottom: 30px; }}
        .slot {{ border: 2px solid #ddd; padding: 15px; border-radius: 5px; text-align: center; }}
        .slot.free {{ background: #E8F5E9; border-color: #4CAF50; }}
        .slot.occupied {{ background: #FFEBEE; border-color: #F44336; }}
        .slot h3 {{ margin-bottom: 10px; color: #333; }}
        .slot .status {{ font-size: 18px; font-weight: bold; margin: 10px 0; }}
        .slot p {{ margin: 5px 0; color: #666; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background: #2196F3; color: white; }}
        tr:hover {{ background: #f5f5f5; }}
        h2 {{ color: #333; margin: 20px 0 10px 0; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Smart Parking System</h1>
        <div class="status-bar">
            <div class="status-item">
                <h3>Total Slots</h3>
                <p>{TOTAL_SLOTS}</p>
            </div>
            <div class="status-item">
                <h3>Free</h3>
                <p>{free_count}</p>
            </div>
            <div class="status-item">
                <h3>Occupied</h3>
                <p>{occupied_count}</p>
            </div>
            <div class="status-item">
                <h3>Status</h3>
                <p>{status}</p>
            </div>
        </div>
        
        <h2>Parking Slots</h2>
        <div class="slots">
            {slot_panels}
        </div>
        
        <h2>Active Tickets (OPEN)</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Slot</th>
                <th>Time-In</th>
                <th>Elapsed</th>
            </tr>
            {active_tickets}
        </table>
        
        <h2>Recent Tickets (CLOSED)</h2>
        <table>
            <tr>
                <th>ID</th>
                <th>Slot</th>
                <th>Duration</th>
                <th>Fee</th>
                <th>Time-Out</th>
            </tr>
            {recent_tickets}
        </table>
    </div>
</body>
</html>"""
        return html
    
    def handle_client(self):
        try:
            client, addr = self.server_socket.accept()
            client.settimeout(1.0)
            request = client.recv(1024).decode()
            
            if "GET" in request:
                response = self.get_web_page()
                client.send("HTTP/1.1 200 OK\r\n")
                client.send("Content-Type: text/html\r\n")
                client.send("Connection: close\r\n\r\n")
                client.sendall(response)
            
            client.close()
        except OSError:
            pass
        except Exception as e:
            print("Web error:", e)
    
    def run(self):
        print("Parking system running...")
        while True:
            try:
                self.check_ultrasonic()
                self.check_slots()
                self.handle_client()
                
                # Auto-close gate
                if self.gate_open:
                    if utime.ticks_diff(utime.ticks_ms(), self.gate_open_time) > GATE_OPEN_TIME:
                        self.close_gate()
                
                time.sleep_ms(10)
            except Exception as e:
                print("Error:", e)
                time.sleep(1)


# ==================== MAIN ====================
if __name__ == "__main__":
    parking = ParkingSystem()
    parking.run()