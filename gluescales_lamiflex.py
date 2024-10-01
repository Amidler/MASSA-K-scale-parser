import socket
import struct
import random
import schedule
import time
import mysql.connector
from mysql.connector import errorcode


###      CONFIG SECTION    ###

# IP address and port of the scale device
ip = "192.168.100.100" # scales IP addres
port = 5001 # scales TCP port 

# MySQL connection configuration
config = {
    'user': 'username',
    'password': 'password4db',
    'host': 'localhost',
    'database': 'database name',
}

### END OF CONFIGURATION SECTION ###


def crc16(data):
    """
    Calculate the CRC16 checksum for the given data.
    The algorithm uses the polynomial 0x1021.
    
    Args:
        data (bytes): Input data for checksum.
    
    Returns:
        bytes: 2-byte CRC16 checksum in big-endian format.
    """
    crc = 0
    for byte in data:
        acc = 0
        temp = (crc >> 8) << 8

        for _ in range(8):
            if (temp ^ acc) & 0x8000:
                acc = (acc << 1) ^ 0x1021
            else:
                acc <<= 1
            temp <<= 1

        crc = acc ^ (crc << 8) ^ (byte & 0xFFFF)

    return struct.pack('>h', crc)  # Big-endian format

def find_scale():
    """
    Discover the scale using a broadcast UDP message.
    
    Returns:
        tuple: The IP address and port of the found scale.
    """
    HEADER = b'\xf8\x55\xce'
    CMD_UDP_POLL = b'\x00'  # Command to discover the scale
    data = HEADER + struct.pack('>H', len(CMD_UDP_POLL)) + CMD_UDP_POLL + crc16(CMD_UDP_POLL)

    # Create a UDP socket and enable broadcasting
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.settimeout(5)  # 5 seconds timeout
    sock.sendto(data, (ip, port))  # Send the broadcast message

    try:
        # Wait for the scale to respond
        buf, addr = sock.recvfrom(1024)
    except socket.timeout:
        addr = None  # Return None if no scale is found
    finally:
        sock.close()

    return addr

def send_tcp(message, scale):
    """
    Send a message to the scale over TCP and receive the response.
    
    Args:
        message (bytes): Command message to send.
        scale (tuple): IP address and port of the scale.
    
    Returns:
        bytes: Response from the scale.
    """
    HEADER = b'\xf8\x55\xce'
    data = HEADER + struct.pack('>H', len(message)) + message + crc16(message)

    # Create a TCP socket and connect to the scale
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(scale)

    # Send the data and wait for the response
    sock.sendall(data)
    result = sock.recv(1024)
    sock.close()

    return result

def parse_weight(resp):
    """
    Parse the weight response from the scale.
    
    Args:
        resp (bytes): Response data from the scale.
    
    Returns:
        dict: Parsed weight data including weight, division, and stability.
    """
    # Unpack the response based on known structure
    header, length, command, weight, division, stable, crc = struct.unpack('<3sHBIbB2s', resp)
    
    # Convert to a dictionary for easier processing
    parsed_data = {
        'Header': header,
        'Length': length,
        'Command': command,
        'Weight': weight,
        'Division': division,
        'Stable': stable,
        'CRC': crc
    }

    return parsed_data    

def check_and_insert_data(parsed_data, connected):
    """
    Check if the table exists in MySQL and insert the parsed data.
    
    Args:
        parsed_data (dict): Parsed scale data.
        connected (int): Connection status flag (1 for connected, 0 for not connected).
    """

    # Query to create the table if it does not exist
    create_table_query = """
    CREATE TABLE IF NOT EXISTS GlueScales1 (
        id INT NOT NULL AUTO_INCREMENT,
        weight INT NOT NULL,
        division INT NOT NULL,
        stable INT NOT NULL,
        connected INT NOT NULL,
        datetime DATETIME DEFAULT CURRENT_TIMESTAMP,
        PRIMARY KEY (id)
    );
    """

    # Query to insert data
    insert_data_query = """
    INSERT INTO GlueScales1 (weight, division, stable, connected)
    VALUES (%s, %s, %s, %s);
    """

    try:
        # Connect to MySQL
        connection = mysql.connector.connect(**config)
        cursor = connection.cursor()

        # Ensure the table exists
        cursor.execute(create_table_query)
        connection.commit()

        if connected:
            # Insert the parsed data
            weight = parsed_data['Weight']
            division = parsed_data['Division']
            stable = parsed_data['Stable']
            cursor.execute(insert_data_query, (weight, division, stable, connected))
        else:
            # Insert a "not connected" entry
            cursor.execute(insert_data_query, (0, 0, 0, connected))
        
        connection.commit()
        print("Data successfully inserted into the table.")
    
    except mysql.connector.Error as err:
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Access denied: Invalid username or password.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist.")
        else:
            print(err)
    
    finally:
        # Close cursor and connection
        cursor.close()
        connection.close()

def main():
    """
    Main function to find the scale, retrieve data, and store it in the database.
    """
    # Find the scale using UDP
    scale = find_scale()
    if scale:
        print(f'Scale found at {scale[0]}:{scale[1]}')
        
        # Send a command to get the weight
        resp = send_tcp(b'\xA0', scale)
        if resp:
            print("Response received:", resp)
            
            # Parse and insert the data into the database
            parsed_data = parse_weight(resp)
            print("Parsed data:", parsed_data)
            check_and_insert_data(parsed_data, connected=1)
        else:
            print("No response received from the scale.")
    else:
        print("No scale found.")

# Schedule the main function to run every 1 minute
schedule.every(1).minutes.do(main)

# Main loop to keep the scheduler running
while True:
    schedule.run_pending()
    time.sleep(1)
