import random
import socket
import time
import threading

# Global lock for thread-safe port allocation
_port_lock = threading.Lock()

def check_port_available(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(('0.0.0.0', port))
        return True
    except OSError:
        time.sleep(0.1)  # Short delay to further reduce chance of collisions
        return False
    finally:
        sock.close()

allocated_ports = set()

def find_available_tcp_port(
    min_port: int = 30000, max_port: int = 39999, max_attempts: int = 10
) -> int:
    """Find an available TCP port in a specified range.

    Args:
        min_port (int): The lower bound of the port range (default: 30000)
        max_port (int): The upper bound of the port range (default: 39999)
        max_attempts (int): Maximum number of attempts to find an available port (default: 10)

    Returns:
        int: An available port number, or -1 if none found after max_attempts
    """
    global allocated_ports
    rng = random.SystemRandom()
    ports = list(range(min_port, max_port + 1))
    rng.shuffle(ports)

    for port in ports[:max_attempts]:
        with _port_lock:  # Ensure atomic port check and allocation
            if port not in allocated_ports and check_port_available(port):
                allocated_ports.add(port)
                return port
    return -1


def display_number_matrix(number: int) -> str | None:
    if not 0 <= number <= 999:
        return None

    # Define the matrix representation for each digit
    digits = {
        '0': ['###', '# #', '# #', '# #', '###'],
        '1': ['  #', '  #', '  #', '  #', '  #'],
        '2': ['###', '  #', '###', '#  ', '###'],
        '3': ['###', '  #', '###', '  #', '###'],
        '4': ['# #', '# #', '###', '  #', '  #'],
        '5': ['###', '#  ', '###', '  #', '###'],
        '6': ['###', '#  ', '###', '# #', '###'],
        '7': ['###', '  #', '  #', '  #', '  #'],
        '8': ['###', '# #', '###', '# #', '###'],
        '9': ['###', '# #', '###', '  #', '###'],
    }

    # alternatively, with leading zeros: num_str = f"{number:03d}"
    num_str = str(number)  # Convert to string without padding

    result = []
    for row in range(5):
        line = ' '.join(digits[digit][row] for digit in num_str)
        result.append(line)

    matrix_display = '\n'.join(result)
    return f'\n{matrix_display}\n'
