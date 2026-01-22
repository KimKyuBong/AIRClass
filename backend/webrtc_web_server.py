import http.server
import socketserver
import os

PORT = 8000
DIRECTORY = "static_streaming"


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)


print(f"Serving WebRTC viewer at http://localhost:{PORT}/webrtc_viewer.html")
print(f"Make sure MediaMTX is running on port 8889 for WebRTC")

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    httpd.serve_forever()
