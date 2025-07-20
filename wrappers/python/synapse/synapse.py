import serial
import time
import glob # For listing serial ports

class PicoGPIO:
    def __init__(self, port=None, baud_rate=115200, timeout=1, expected_id=None):
        self.ser = None
        self.board_id = None
        self.baud_rate = baud_rate
        self.timeout = timeout
        
        if port:
            self.connect(port)
        else:
            self.auto_detect_and_connect(expected_id)

    def _send_command(self, command_char, *args):
        if not self.ser or not self.ser.is_open:
            print("Not connected to Pico.")
            return None
        
        # Clear any pending input before sending a new command
        while self.ser.in_waiting:
            self.ser.read_all()

        cmd_string = command_char
        for arg in args:
            cmd_string += str(arg) + " " # Add space separator
        cmd_string = cmd_string.strip() # Remove trailing space
        
        self.ser.write(cmd_string.encode('utf-8') + b'\n') # Send with newline
        
        response = ""
        start_time = time.time()
        while (time.time() - start_time) < self.timeout:
            if self.ser.in_waiting:
                response_line = self.ser.readline().decode('utf-8').strip()
                if response_line:
                    # Look for our ACK or Error prefix
                    if response_line.startswith('A') or response_line.startswith('E'):
                        return response_line
                    else:
                        # Sometimes extra lines appear during startup or other prints
                        response = response_line # Keep the last relevant line if no prefix
            time.sleep(0.01) # Small delay to avoid busy-waiting
        
        return response # Return whatever we got, even if not an ACK/Error

    def _check_pico_id(self, port):
        """Attempts to connect to a port and get its ID."""
        temp_ser = None
        try:
            temp_ser = serial.Serial(port, self.baud_rate, timeout=1) # Short timeout for ID check
            time.sleep(2) # Give Pico time to boot and send initial message
            
            # Clear initial messages
            while temp_ser.in_waiting:
                temp_ser.readline() 

            # Send GET_BOARD_ID command
            temp_ser.write(b'g\n') # 'g' for GET_BOARD_ID, followed by newline
            
            response = ""
            start_time = time.time()
            # Wait for response, looking for 'A' followed by 'ID:'
            while (time.time() - start_time) < 2: # Give 2 seconds for ID response
                if temp_ser.in_waiting:
                    line = temp_ser.readline().decode('utf-8').strip()
                    if line.startswith('AID:'): # Acknowledgment + ID prefix
                        return line[4:] # Return the ID part
                time.sleep(0.01) # Small delay
            return None # No valid ID response
        except (serial.SerialException, OSError):
            return None
        finally:
            if temp_ser and temp_ser.is_open:
                temp_ser.close()

    def auto_detect_and_connect(self, expected_id=None):
        """
        Automatically detects and connects to a Pico, optionally checking for a specific ID.
        """
        print("Attempting to auto-detect Pico...")
        # Common serial port patterns for different OS
        ports = []
        if sys.platform.startswith('linux'):
            ports = glob.glob('/dev/ttyACM*') + glob.glob('/dev/ttyUSB*')
        elif sys.platform.startswith('darwin'):
            ports = glob.glob('/dev/cu.usbmodem*') + glob.glob('/dev/tty.usbserial*')
        elif sys.platform.startswith('win'):
            # Iterate through COM ports 1 to 20 (adjust if needed)
            for i in range(1, 21):
                ports.append(f'COM{i}')
        else:
            print("Unsupported OS for auto-detection.")
            return

        for port in ports:
            print(f"Checking port: {port}")
            board_id = self._check_pico_id(port)
            if board_id:
                print(f"Found Pico with ID: '{board_id}' on {port}")
                if expected_id and board_id != expected_id:
                    print(f"ID mismatch: Expected '{expected_id}', got '{board_id}'. Skipping.")
                    continue
                
                print(f"Connecting to {port} with ID '{board_id}'...")
                self.connect(port)
                if self.ser and self.ser.is_open:
                    self.board_id = board_id # Store the ID once connected
                    return
        
        print("No Pico found or connected.")

    def connect(self, port):
        """Establishes a direct connection to a specified serial port."""
        if self.ser and self.ser.is_open:
            self.ser.close()
        
        try:
            self.ser = serial.Serial(port, self.baud_rate, timeout=self.timeout)
            time.sleep(2) # Give the serial connection time to establish
            # Clear any initial messages from the Arduino boot
            while self.ser.in_waiting:
                self.ser.readline().decode('utf-8').strip()
            print(f"Connected to Pico on {port}")
        except serial.SerialException as e:
            print(f"Error connecting to Pico on {port}: {e}")
            self.ser = None
        except OSError as e: # Catch permissions issues, non-existent ports etc.
            print(f"OS error connecting to {port}: {e}")
            self.ser = None

    def set_pin_mode(self, pin, mode):
        """
        Sets the mode of a GPIO pin.
        :param pin: The GPIO pin number.
        :param mode: "input" or "output".
        """
        arduino_mode = 0 if mode.lower() == "input" else 1
        return self._send_command('m', pin, arduino_mode)

    def digital_write(self, pin, value):
        """
        Writes a digital value (HIGH or LOW) to a GPIO pin.
        :param pin: The GPIO pin number.
        :param value: True/False, 1/0, "high"/"low"
        """
        if isinstance(value, str):
            arduino_value = 1 if value.lower() == "high" else 0
        elif isinstance(value, bool):
            arduino_value = 1 if value else 0
        else:
            arduino_value = 1 if value else 0 # Handles 1/0 integers

        return self._send_command('w', pin, arduino_value)

    def digital_read(self, pin):
        """
        Reads the digital value of a GPIO pin.
        :param pin: The GPIO pin number.
        :return: "HIGH" or "LOW" string.
        """
        response = self._send_command('r', pin)
        if response and response.startswith('A'): # Check for acknowledgment
            data = response[1:] # Remove 'A'
            if "HIGH" in data:
                return "HIGH"
            elif "LOW" in data:
                return "LOW"
        return None

    def set_pull_resistor(self, pin, resistor_type):
        """
        Sets the pull-up or pull-down resistor for a pin.
        :param pin: The GPIO pin number.
        :param resistor_type: "pullup", "pulldown", or "disable".
        """
        arduino_type = 0 # INPUT_PULLUP
        if resistor_type.lower() == "pulldown":
            arduino_type = 1 # INPUT_PULLDOWN
        elif resistor_type.lower() == "disable":
            arduino_type = 2 # INPUT (effectively disables)
        
        return self._send_command('p', pin, arduino_type)

    def set_board_id(self, new_id):
        """
        Sets a new ID for the connected Pico board. This ID will persist across reboots.
        :param new_id: The new ID string (max 16 characters).
        :return: Response from the Pico.
        """
        if len(new_id) > 16:
            print("Warning: Board ID will be truncated to 16 characters.")
            new_id = new_id[:16]
        response = self._send_command('i', new_id) # 'i' for SET_BOARD_ID
        if response and response.startswith('A'):
            self.board_id = new_id # Update local ID
            print(f"Board ID successfully set to: {new_id}")
        else:
            print(f"Failed to set board ID. Response: {response}")
        return response

    def get_board_id(self):
        """
        Retrieves the ID of the connected Pico board.
        :return: The board ID string or None if not found/connected.
        """
        if self.board_id: # If already detected and stored
            return self.board_id
        
        response = self._send_command('g') # 'g' for GET_BOARD_ID
        if response and response.startswith('AID:'):
            self.board_id = response[4:] # Store and return the ID part
            return self.board_id
        return None

    def close(self):
        """Closes the serial connection."""
        if self.ser and self.ser.is_open:
            self.ser.close()
            print("Serial connection closed.")

# --- Example Usage ---
if __name__ == "__main__":
    import sys

    print("--- Auto-detecting Pico (any ID) ---")
    pico = PicoGPIO() # Auto-detect any Pico
    if pico.ser and pico.ser.is_open:
        print(f"Successfully connected to Pico with ID: '{pico.get_board_id()}'")
        
        # Example: Set a custom ID
        print("\n--- Setting a custom ID ---")
        new_custom_id = "MY_SPECIAL_PICO"
        response = pico.set_board_id(new_custom_id)
        print(f"Set ID response: {response}")
        print(f"Current Pico ID (after setting): {pico.get_board_id()}")
        
        pico.close()
        
        print("\n--- Auto-detecting Pico with specific ID ---")
        # You'll need to replug the Pico or restart the script to make the new ID active
        # Or, the Python script needs to close the old connection and open a new one
        # to re-read the ID from the device.
        pico_with_id = PicoGPIO(expected_id=new_custom_id)
        if pico_with_id.ser and pico_with_id.ser.is_open:
            print(f"Connected to specific Pico ID: '{pico_with_id.get_board_id()}'")
            print(pico_with_id.set_pin_mode(25, "output"))
            print(pico_with_id.digital_write(25, "high"))
            time.sleep(0.5)
            print(pico_with_id.digital_write(25, "low"))
            time.sleep(0.5)
            pico_with_id.close()
        else:
            print(f"Could not find Pico with ID '{new_custom_id}'.")
    else:
        print("No Pico detected for general testing.")

    print("\n--- Manual Connection Example (if auto-detect fails or you know the port) ---")
    # Replace with your Pico's serial port if you want to test manual connection
    # pico_port_manual = "/dev/ttyACM0" 
    # pico_manual = PicoGPIO(port=pico_port_manual)
    # if pico_manual.ser and pico_manual.ser.is_open:
    #     print(f"Manually connected to Pico ID: '{pico_manual.get_board_id()}'")
    #     pico_manual.close()
    # else:
    #     print(f"Manual connection to {pico_port_manual} failed.")