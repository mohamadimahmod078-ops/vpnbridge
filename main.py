import threading
import socket
import select
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.clock import Clock

BUFFER_SIZE = 65536
CONNECT_TIMEOUT = 15
IDLE_TIMEOUT = 300

class ProxyHandler:
    def __init__(self, client_socket):
        self.client_socket = client_socket

    def handle(self):
        try:
            request = self.client_socket.recv(BUFFER_SIZE)
            if not request:
                self.client_socket.close()
                return
            
            headers = request.split(b'\r\n')
            first_line = headers[0].decode('utf-8', errors='ignore').split()
            if len(first_line) < 3:
                self.client_socket.close()
                return
            
            method, url = first_line[0], first_line[1]
            
            if method == 'CONNECT':
                host, port = url.split(':')
                port = int(port)
                self.tunnel(host, port)
            else:
                self.client_socket.close() # Simplified for this demo
        except Exception as e:
            self.client_socket.close()

    def tunnel(self, host, port):
        try:
            remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            remote_socket.settimeout(CONNECT_TIMEOUT)
            remote_socket.connect((host, port))
            self.client_socket.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')
            
            sockets = [self.client_socket, remote_socket]
            while True:
                r, _, _ = select.select(sockets, [], [], IDLE_TIMEOUT)
                if not r:
                    break
                for s in r:
                    data = s.recv(BUFFER_SIZE)
                    if not data:
                        return
                    if s is self.client_socket:
                        remote_socket.sendall(data)
                    else:
                        self.client_socket.sendall(data)
        except Exception:
            pass
        finally:
            self.client_socket.close()
            try:
                remote_socket.close()
            except:
                pass

def start_proxy():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', 8080))
    server.listen(100)
    while True:
        try:
            client, addr = server.accept()
            threading.Thread(target=ProxyHandler(client).handle, daemon=True).start()
        except:
            break

class PanelHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        html = "<html dir='rtl'><body><h1>پنل Termux VPN Bridge</h1><p>پروکسی در پورت 8080 در حال اجراست.</p></body></html>"
        self.wfile.write(html.encode('utf-8'))

def start_panel():
    server = ThreadingHTTPServer(('0.0.0.0', 5000), PanelHandler)
    server.serve_forever()

class VPNBridgeApp(App):
    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        self.status_label = Label(text="در حال راه‌اندازی سرورها...")
        self.layout.add_widget(self.status_label)
        
        threading.Thread(target=start_proxy, daemon=True).start()
        threading.Thread(target=start_panel, daemon=True).start()
        
        Clock.schedule_once(self.update_status, 2)
        return self.layout

    def update_status(self, dt):
        self.status_label.text = "سرور پروکسی: پورت 8080\nپنل وب: پورت 5000\nوضعیت: در حال اجرا"

if __name__ == '__main__':
    VPNBridgeApp().run()
