#!/usr/bin/env python3
import http.server
import socketserver
import os

PORT = 8000
DIRECTORY = "build"

def getProjectRoot():
    return os.path.dirname(os.path.realpath(__file__))

def serve():

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=os.path.join(getProjectRoot(), DIRECTORY), **kwargs)

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        print(f"Serving site at localhost:{PORT}")
        httpd.serve_forever()


if __name__=='__main__':
    serve()
