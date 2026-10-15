from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import socketserver

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        body = json.dumps({"status": "ready"}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, *args):
        pass

class Server(HTTPServer):
    def server_bind(self):
        # HTTPServer resolves its host name here, which can stall for seconds on CI runners.
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = "127.0.0.1", self.server_address[1]

if __name__ == "__main__":
    server = Server(("127.0.0.1", 0), Handler)
    print(server.server_port, flush=True)
    server.serve_forever()

