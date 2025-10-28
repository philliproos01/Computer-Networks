import socket

# Server info
server_ip = "192.168.137.1"  # Or the server's actual IP address
server_port = 6789

# Create TCP socket
client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((server_ip, server_port))

# Send HTTP GET request for /index.html
request = "GET /index.html HTTP/1.1\r\nHost: localhost\r\n\r\n"
client_socket.send(request.encode())

# Receive and print response
response = client_socket.recv(4096)
print(response.decode())

client_socket.close()
