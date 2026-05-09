#!/usr/bin/env python3
"""
MUD proxy: connects to ROM on port 4000, logs output to /tmp/mud.log,
reads commands from /tmp/mud.cmd (one per line, written by send_mud.py).
"""
import socket
import threading
import time
import os
import re
import sys

MUD_HOST = '127.0.0.1'
MUD_PORT = 4000
LOG_FILE = '/tmp/mud.log'
CMD_FILE = '/tmp/mud.cmd'

ANSI = re.compile(r'\x1b\[[0-9;]*[mABCDEFGHJKSTfnsu]')

def strip_ansi(text):
    return ANSI.sub('', text)

def log(text):
    with open(LOG_FILE, 'a') as f:
        f.write(text)

def receiver(sock):
    buf = b''
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                log('\n[** Connection closed by server **]\n')
                break
            buf += data
            text = buf.decode('latin-1', errors='replace')
            buf = b''
            text = strip_ansi(text).replace('\r\n', '\n').replace('\r', '\n')
            log(text)
        except Exception as e:
            log(f'\n[** Receiver error: {e} **]\n')
            break

def commander(sock):
    # Watch for new lines in CMD_FILE
    if not os.path.exists(CMD_FILE):
        open(CMD_FILE, 'w').close()
    pos = os.path.getsize(CMD_FILE)
    while True:
        time.sleep(0.1)
        try:
            size = os.path.getsize(CMD_FILE)
            if size > pos:
                with open(CMD_FILE, 'r') as f:
                    f.seek(pos)
                    new = f.read()
                pos = size
                for line in new.splitlines():
                    cmd = line.strip()
                    if cmd:
                        sock.sendall((cmd + '\r\n').encode('latin-1'))
                        time.sleep(0.05)
        except Exception as e:
            log(f'\n[** Commander error: {e} **]\n')

if __name__ == '__main__':
    # Clear log
    open(LOG_FILE, 'w').close()
    open(CMD_FILE, 'w').close()

    print(f'Connecting to MUD at {MUD_HOST}:{MUD_PORT}...')
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((MUD_HOST, MUD_PORT))
    print(f'Connected. Logging to {LOG_FILE}, commands via {CMD_FILE}')

    t1 = threading.Thread(target=receiver, args=(sock,), daemon=True)
    t2 = threading.Thread(target=commander, args=(sock,), daemon=True)
    t1.start()
    t2.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
