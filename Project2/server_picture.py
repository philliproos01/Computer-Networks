from socket import *
import sys

serverSocket = socket(AF_INET, SOCK_STREAM)
serverPort = 6789
serverSocket.bind(("", serverPort))
serverSocket.listen(1)

while True:
    print('The server is ready to receive')
    connectionSocket, addr = serverSocket.accept()
    try:
        message = connectionSocket.recv(1024).decode()
        filename = message.split()[1][1:]  # remove leading slash

        # Guess Content-Type based on extension (without mimetypes)
        if filename.endswith('.png'):
            content_type = 'image/png'
        elif filename.endswith('.jpg') or filename.endswith('.jpeg'):
            content_type = 'image/jpeg'
        elif filename.endswith('.gif'):
            content_type = 'image/gif'
        else:
            content_type = 'application/octet-stream'

        # Open file in binary mode
        with open(filename, 'rb') as f:
            outputdata = f.read()

        header = f"HTTP/1.1 200 OK\r\nContent-Type: {content_type}\r\n\r\n"
        connectionSocket.send(header.encode())
        connectionSocket.sendall(outputdata)
        connectionSocket.close()
    except IOError:
        header = "HTTP/1.1 404 Not Found\r\nContent-Type: text/html\r\n\r\n"
        body = "<html><head></head><body><h1>404 Not Found</h1></body></html>\r\n"
        connectionSocket.send(header.encode())
        connectionSocket.send(body.encode())
        connectionSocket.close()

serverSocket.close()
sys.exit()
