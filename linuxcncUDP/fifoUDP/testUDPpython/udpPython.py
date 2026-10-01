# udp_send.py
import socket
import time

UDP_IP = "127.0.0.1"
UDP_PORT = 5000

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

while True:
    msg = "123.45:67.89:12.34:"
    sock.sendto(msg.encode(), (UDP_IP, UDP_PORT))
    print("Gönderildi:", msg)
    time.sleep(1)

