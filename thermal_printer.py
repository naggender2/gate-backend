# import socket
# import json
# from escpos.printer import File
# from bs4 import BeautifulSoup  # For HTML parsing

# def start_server():
#     host = "localhost"
#     port = 9999  # Port for the local server
    
#     # Create a socket object
#     server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
#     server_socket.bind((host, port))
#     server_socket.listen(1)
#     print(f"Listening for print commands on {host}:{port}...")

#     while True:
#         client_socket, addr = server_socket.accept()
#         print(f"Connection from {addr}")
#         try:
#             # Receive data
#             request = client_socket.recv(4096).decode('utf-8')  # Increased buffer size for large requests
#             print("Received data:", request)

#             # Split request into headers and body
#             headers, _, body = request.partition("\r\n\r\n")

#             # Handle CORS preflight (OPTIONS request)
#             if headers.startswith("OPTIONS"):
#                 client_socket.sendall(
#                     b"HTTP/1.1 200 OK\r\n"
#                     b"Access-Control-Allow-Origin: *\r\n"
#                     b"Access-Control-Allow-Methods: POST, OPTIONS\r\n"
#                     b"Access-Control-Allow-Headers: content-type\r\n"
#                     b"\r\n"
#                 )
#                 print("CORS preflight request handled")
#             else:
#                 # Determine Content-Type and handle accordingly
#                 if "Content-Type: application/json" in headers:
#                     try:
#                         data_json = json.loads(body.strip())
#                         print_pass(data_json)
#                         send_response(client_socket, "Print success")
#                     except json.JSONDecodeError:
#                         raise ValueError("Invalid JSON data received")
#                 elif "Content-Type: text/html" in headers:
#                     try:
#                         print_pass_from_html(body.strip())
#                         send_response(client_socket, "Print success")
#                     except Exception as e:
#                         raise ValueError(f"Error processing HTML: {e}")
#                 else:
#                     raise ValueError("Unsupported Content-Type")

#         except Exception as e:
#             print("Error:", str(e))
#             send_response(client_socket, f"Print failed: {str(e)}", status="400 Bad Request")
#         finally:
#             client_socket.close()


# def send_response(client_socket, message, status="200 OK"):
#     """Send HTTP response to client."""
#     client_socket.sendall(
#         f"HTTP/1.1 {status}\r\n"
#         f"Access-Control-Allow-Origin: *\r\n"
#         f"Content-Type: text/plain\r\n"
#         f"\r\n"
#         f"{message}".encode('utf-8')
#     )


# def print_pass(data):
#     thermal_printer = File("/dev/usb/lp0")

#     # Printing logic
#     thermal_printer.set(bold=True, align='center', double_width=True)
#     thermal_printer.text("BITS ENTRY-EXIT PASS\n")
#     thermal_printer.set(bold=False, align='left', double_width=False)
#     thermal_printer.text(f"ID: {data['entry_id']}\n")
#     thermal_printer.text(f"Name: {data['name'].upper()}\n")
#     thermal_printer.text(f"Contact No: {data['contact_no']}\n")
#     thermal_printer.text(f"Vehicle No: {data['vehicle_no'].upper()}\n")
#     thermal_printer.text(f"Where To Go: {data['destination'].upper()}\n")
#     thermal_printer.text(f"Reason: {data['reason'].upper()}\n")
#     thermal_printer.text(f"In Time: {data['in_time']}\n")
#     thermal_printer.text(f"Remarks: {data['remarks']}\n")
#     thermal_printer.text("Please Return this Pass at BITS Main Gate\n")
#     thermal_printer.qr(f"{data['entry_id']},{data['name']}", size=5, model=2)
#     thermal_printer.cut()
#     thermal_printer.close()


# def print_pass_from_html(html_data):
#     thermal_printer = File("/dev/usb/lp0")

#     # Parse the HTML content
#     soup = BeautifulSoup(html_data, "html.parser")
#     entry_id = soup.find("strong", text="ID:").next_sibling.strip()
#     name = soup.find("strong", text="Name:").next_sibling.strip()
#     contact_no = soup.find("strong", text="Contact No.:").next_sibling.strip()
#     vehicle_no = soup.find("strong", text="Vehicle No.:").next_sibling.strip()
#     destination = soup.find("strong", text="Where To Go:").next_sibling.strip()
#     reason = soup.find("strong", text="Reason:").next_sibling.strip()
#     in_time = soup.find("strong", text="In Time:").next_sibling.strip()
#     remarks = soup.find("strong", text="Remarks:").next_sibling.strip()

#     # Printing logic
#     thermal_printer.set(bold=True, align='center', double_width=True)
#     thermal_printer.text("BITS ENTRY-EXIT PASS\n")
#     thermal_printer.set(bold=False, align='left', double_width=False)
#     thermal_printer.text(f"ID: {entry_id}\n")
#     thermal_printer.text(f"Name: {name.upper()}\n")
#     thermal_printer.text(f"Contact No: {contact_no}\n")
#     thermal_printer.text(f"Vehicle No: {vehicle_no.upper()}\n")
#     thermal_printer.text(f"Where To Go: {destination.upper()}\n")
#     thermal_printer.text(f"Reason: {reason.upper()}\n")
#     thermal_printer.text(f"In Time: {in_time}\n")
#     thermal_printer.text(f"Remarks: {remarks}\n")
#     thermal_printer.text("Please Return this Pass at BITS Main Gate\n")
#     thermal_printer.qr(f"{entry_id},{name}", size=5, model=2)
#     thermal_printer.cut()
#     thermal_printer.close()


# if __name__ == "__main__":
#     start_server()


import socket
import json
from escpos.printer import File
from bs4 import BeautifulSoup  # For HTML parsing

def start_server():
    host = "localhost"
    port = 9999  # Port for the local server
    
    # Create a socket object
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((host, port))
    server_socket.listen(1)
    print(f"Listening for print commands on {host}:{port}...")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"Connection from {addr}")
        try:
            # Receive data
            request = client_socket.recv(4096).decode('utf-8')  # Increased buffer size for large requests
            print("Received data:", request)

            # Split request into headers and body
            headers, _, body = request.partition("\r\n\r\n")

            # Handle CORS preflight (OPTIONS request)
            if headers.startswith("OPTIONS"):
                client_socket.sendall(
                    b"HTTP/1.1 200 OK\r\n"
                    b"Access-Control-Allow-Origin: *\r\n"
                    b"Access-Control-Allow-Methods: POST, OPTIONS\r\n"
                    b"Access-Control-Allow-Headers: content-type\r\n"
                    b"\r\n"
                )
                print("CORS preflight request handled")
            else:
                # Determine Content-Type and handle accordingly
                if "Content-Type: application/json" in headers:
                    try:
                        data_json = json.loads(body.strip())
                        print_pass(data_json)
                        send_response(client_socket, "Print success")
                    except json.JSONDecodeError:
                        raise ValueError("Invalid JSON data received")
                elif "Content-Type: text/html" in headers:
                    try:
                        print_pass_from_html(body.strip())
                        send_response(client_socket, "Print success")
                    except Exception as e:
                        raise ValueError(f"Error processing HTML: {e}")
                else:
                    raise ValueError("Unsupported Content-Type")

        except Exception as e:
            print("Error:", str(e))
            send_response(client_socket, f"Print failed: {str(e)}", status="400 Bad Request")
        finally:
            client_socket.close()


def send_response(client_socket, message, status="200 OK"):
    """Send HTTP response to client."""
    client_socket.sendall(
        f"HTTP/1.1 {status}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Content-Type: text/plain\r\n"
        f"\r\n"
        f"{message}".encode('utf-8')
    )


def print_pass(data):
    thermal_printer = File("/dev/usb/lp0")

    # Stylish Printing Logic
    thermal_printer.set(bold=True, align='center', double_width=True, double_height=True)
    thermal_printer.text("--------------------------------\n")
    thermal_printer.text(" BITS ENTRY-EXIT PASS\n")
    thermal_printer.text("--------------------------------\n")
    
    thermal_printer.set(bold=False, align='left', double_width=False)
    thermal_printer.text(f"ID              : {data['entry_id']}\n")
    thermal_printer.text(f"Name            : {data['name'].upper()}\n")
    thermal_printer.text(f"Contact No.     : {data['contact_no']}\n")
    thermal_printer.text(f"Vehicle No.     : {data['vehicle_no'].upper()}\n")
    thermal_printer.text(f"Where To Go     : {data['destination'].upper()}\n")
    thermal_printer.text(f"Reason          : {data['reason'].upper()}\n")
    thermal_printer.text(f"In Time         : {data['in_time']}\n")
    thermal_printer.text(f"Vehicle Type    : {data['vehicle_type'].upper()}\n")
    thermal_printer.text(f"Remarks         : {data['remarks']}\n")
    thermal_printer.text(f"DVR: {data['no_driver']}  "
                          f"ST: {data['no_student']}  "
                          f"VT: {data['no_visitor']}  "
                          f"Total: {data['total']}\n")
    
    thermal_printer.text("--------------------------------\n")
    thermal_printer.set(bold=True, align='center', double_width=False)
    thermal_printer.text("Please Return This Pass\n")
    thermal_printer.text("   At BITS Main Gate\n")
    thermal_printer.text("--------------------------------\n")
    
    # Center QR Code
    thermal_printer.set(align='center')
    thermal_printer.qr(f"{data['entry_id']},{data['name']}", size=5, model=2)
    thermal_printer.text("\n")  # Add some space after the QR code
    thermal_printer.text("--------------------------------\n")
    
    thermal_printer.cut()
    thermal_printer.close()


def print_pass_from_html(html_data):
    thermal_printer = File("/dev/usb/lp0")

    # Parse the HTML content
    soup = BeautifulSoup(html_data, "html.parser")
    entry_id = soup.find("strong", text="ID:").next_sibling.strip()
    name = soup.find("strong", text="Name:").next_sibling.strip()
    contact_no = soup.find("strong", text="Contact No.:").next_sibling.strip()
    vehicle_no = soup.find("strong", text="Vehicle No.:").next_sibling.strip()
    destination = soup.find("strong", text="Where To Go:").next_sibling.strip()
    reason = soup.find("strong", text="Reason:").next_sibling.strip()
    in_time = soup.find("strong", text="In Time:").next_sibling.strip()
    vehicle_type = soup.find("strong", text="Vehicle Type:").next_sibling.strip()
    remarks = soup.find("strong", text="Remarks:").next_sibling.strip()
    no_driver = soup.find("strong", text="Driver:").next_sibling.strip()
    no_student = soup.find("strong", text="Student:").next_sibling.strip()
    no_visitor = soup.find("strong", text="Visitor:").next_sibling.strip()
    total = soup.find("strong", text="Total:").next_sibling.strip()

    # Stylish Printing Logic
    thermal_printer.set(bold=True, align='center', double_width=True, double_height=True)
    thermal_printer.text("------------------------\n")
    thermal_printer.text(" BITS ENTRY-EXIT PASS\n")
    thermal_printer.text("------------------------\n")
    
    thermal_printer.set(bold=False, align='left', double_width=False)
    thermal_printer.text(f"ID              : {entry_id}\n")
    thermal_printer.text(f"Name            : {name.upper()}\n")
    thermal_printer.text(f"Contact No.     : {contact_no}\n")
    thermal_printer.text(f"Vehicle No.     : {vehicle_no.upper()}\n")
    thermal_printer.text(f"Where To Go     : {destination.upper()}\n")
    thermal_printer.text(f"Reason          : {reason.upper()}\n")
    thermal_printer.text(f"DVR: {no_driver}  "
                          f"ST: {no_student}  "
                          f"VT: {no_visitor}  "
                          f"Total: {total}\n")
    thermal_printer.text(f"In Time         : {in_time}\n")
    thermal_printer.text(f"Vehicle Type    : {vehicle_type.upper()}\n")
    thermal_printer.text(f"Remarks         : {remarks}\n")
    
    thermal_printer.set(bold=True, align='center', double_width=False)
    thermal_printer.text("--------------------------------\n")
    thermal_printer.text("Please Return This Pass\n")
    thermal_printer.text("   At BITS Main Gate\n")
    thermal_printer.text("--------------------------------\n")
    
    # Center QR Code
    thermal_printer.set(align='center')
    thermal_printer.qr(f"{entry_id},{name}", size=5, model=2)
    thermal_printer.text("\n")  # Add some space after the QR code
    thermal_printer.set(bold=True, align='center', double_width=False)
    thermal_printer.text("--------------------------------\n")
    
    thermal_printer.cut()
    thermal_printer.close()


if __name__ == "__main__":
    start_server()
