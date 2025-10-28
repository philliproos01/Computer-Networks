import socket
import os
import sys
import threading
import multiprocessing

server_ip = "192.168.56.1"
server_port = 6789
stats_file = "login_stats.txt"

def load_stats():
    if not os.path.exists(stats_file):
        return [0, 0]
    with open(stats_file, "r") as f:
        line = f.read().strip()
        if "," in line:
            parts = line.split(",")
            return [int(parts[0]), int(parts[1])]
        else:
            return [0, 0]

def save_stats(successes, failures):
    with open(stats_file, "w") as f:
        f.write(f"{successes},{failures}")

def build_response(body, status="200 OK", content_type="text/html", extra_headers=None):
    headers = [
        f"HTTP/1.1 {status}",
        f"Content-Type: {content_type}",
        f"Content-Length: {len(body.encode())}",
        "Connection: close"
    ]
    if extra_headers:
        headers.extend(extra_headers)
    header = "\r\n".join(headers) + "\r\n\r\n"
    return header + body

def form_page():
    return """
    <html>
      <head><title>Color Selector</title></head>
      <body>
        <h2>Select a color:</h2>
        <form method="get" action="/">
          <input type="radio" name="color" value="red"> Red<br>
          <input type="radio" name="color" value="green"> Green<br>
          <input type="submit" value="Submit">
        </form>
        <a href="/login">Login</a>
      </body>
    </html>
    """

def color_page(color):
    return f"""
    <html>
      <head><title>Color Selection</title></head>
      <body>
        Your color is <span style="color:{color};">{color}!</span>
        <br><a href="/login">Login</a>
      </body>
    </html>
    """

def login_form_page():
    return """
    <html>
      <head><title>Login</title></head>
      <body>
        <h2>Login</h2>
        <form method="POST" action="/login">
          Username: <input type="text" name="username"><br>
          Password: <input type="password" name="password"><br>
          <input type="submit" value="Login">
        </form>
      </body>
    </html>
    """

def stats_page(success, fail):
    return f"""
    <html>
      <head><title>Login Stats</title></head>
      <body>
        <h2>Login Statistics</h2>
        <p>Successful logins: {success}</p>
        <p>Unsuccessful logins: {fail}</p>
        <br><a href="/">Home</a>
      </body>
    </html>
    """

def error_page(msg="Invalid credentials"):
    return f"""
    <html>
      <head><title>Login Error</title></head>
      <body>
        <h2>{msg}</h2>
        <a href="/login">Try again</a>
      </body>
    </html>
    """

def print_help():
    help_text = """
Server command line help:
 - exit : Close all open sockets and exit the server program.
 - help : Show this help message.
"""
    print(help_text.strip())

def cli_listener(stop_event):
    while not stop_event.is_set():
        cmd = input().strip()
        if cmd == "exit":
            print("Exiting server...")
            stop_event.set()
        elif cmd == "help":
            print_help()
        elif cmd:
            print(f"{cmd}: Command Not Found")

def handle_client(conn, addr, stats_lock):
    print(f"Request from {addr}:")
    try:
        request = conn.recv(4096).decode()
        if not request:
            conn.close()
            return

        request_line = request.splitlines()[0]
        method = request_line.split()[0]
        path = request_line.split()[1]

        # Stats must be synchronized between processes
        successes, failures = load_stats()

        if method == "GET" and (path == "/" or path.startswith("/?")):
            if "color=red" in path:
                body = color_page("red")
            elif "color=green" in path:
                body = color_page("green")
            else:
                body = form_page()
            response = build_response(body)
        elif method == "GET" and "red" in path:
            response = build_response(color_page("red"))
        elif method == "GET" and "green" in path:
            response = build_response(color_page("green"))
        elif method == "GET" and path == "/login":
            body = login_form_page()
            response = build_response(body)
        elif method == "POST" and path == "/login":
            if "\r\n\r\n" in request:
                form_data = request.split("\r\n\r\n", 1)[1]
                params = dict(
                    pair.split("=") if "=" in pair else ('','') for pair in form_data.replace("&", " ").split()
                )
                username = params.get("username", "")
                password = params.get("password", "")
                if username == "admin" and password == "password":
                    # Synchronize file writes using a lock
                    with stats_lock:
                        successes, failures = load_stats()
                        successes += 1
                        save_stats(successes, failures)
                    response = build_response("", status="303 See Other", extra_headers=[f"Location: /stats"])
                else:
                    with stats_lock:
                        successes, failures = load_stats()
                        failures += 1
                        save_stats(successes, failures)
                    body = error_page()
                    response = build_response(body)
            else:
                body = error_page("Malformed request")
                response = build_response(body, status="400 Bad Request")
        elif method == "GET" and path == "/stats":
            successes, failures = load_stats()
            body = stats_page(successes, failures)
            response = build_response(body)
        else:
            body = "<html><body><h1>404 Not Found</h1></body></html>"
            response = build_response(body, status="404 Not Found")

        conn.sendall(response.encode())
    except Exception as e:
        body = f"<html><body><h1>500 Internal Server Error</h1><p>{e}</p></body></html>"
        response = build_response(body, status="500 Internal Server Error")
        conn.sendall(response.encode())
    finally:
        conn.close()

if __name__ == '__main__':
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)

    print(f"Listening on {server_ip}:{server_port}...")
    print_help()

    stop_event = threading.Event()
    stats_lock = multiprocessing.Lock()  # For stats file access across processes

    cli_thread = threading.Thread(target=cli_listener, args=(stop_event,))
    cli_thread.daemon = True
    cli_thread.start()

    try:
        while not stop_event.is_set():
            server_socket.settimeout(1.0)
            try:
                conn, addr = server_socket.accept()
            except socket.timeout:
                continue

            p = multiprocessing.Process(target=handle_client, args=(conn, addr, stats_lock))
            p.daemon = True
            p.start()
    finally:
        server_socket.close()
        print("Server shutdown complete.")
