import socket
import threading
import re
from flask import Flask, render_template
from flask_socketio import SocketIO, emit

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mudclient'
socketio = SocketIO(app, cors_allowed_origins='*', async_mode='threading')

MUD_HOST = '127.0.0.1'
MUD_PORT = 4000

mud_socket = None
mud_lock = threading.Lock()

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')
ANSI_COLOR_MAP = {
    '30': '#555', '31': '#e74c3c', '32': '#2ecc71', '33': '#f1c40f',
    '34': '#3498db', '35': '#9b59b6', '36': '#1abc9c', '37': '#ecf0f1',
    '90': '#888', '91': '#ff6b6b', '92': '#55efc4', '93': '#ffeaa7',
    '94': '#74b9ff', '95': '#fd79a8', '96': '#81ecec', '97': '#ffffff',
    '1;30': '#888', '1;31': '#ff6b6b', '1;32': '#55efc4', '1;33': '#ffeaa7',
    '1;34': '#74b9ff', '1;35': '#fd79a8', '1;36': '#81ecec', '1;37': '#ffffff',
}

def ansi_to_html(text):
    result = []
    i = 0
    current_style = None
    while i < len(text):
        if text[i] == '\x1b' and i + 1 < len(text) and text[i+1] == '[':
            j = i + 2
            while j < len(text) and text[j] not in 'mABCDEFGHJKSTfnsu':
                j += 1
            if j < len(text) and text[j] == 'm':
                code = text[i+2:j]
                if current_style:
                    result.append('</span>')
                    current_style = None
                if code == '0' or code == '':
                    pass
                elif code in ANSI_COLOR_MAP:
                    color = ANSI_COLOR_MAP[code]
                    result.append(f'<span style="color:{color}">')
                    current_style = code
                else:
                    parts = code.split(';')
                    color_code = ';'.join(p for p in parts if p in ANSI_COLOR_MAP or p in ('1',))
                    # try bold+color
                    if len(parts) == 2 and parts[0] == '1' and parts[1] in ANSI_COLOR_MAP:
                        color = ANSI_COLOR_MAP[parts[1]]
                        result.append(f'<span style="color:{color};font-weight:bold">')
                        current_style = code
                    elif parts[-1] in ANSI_COLOR_MAP:
                        color = ANSI_COLOR_MAP[parts[-1]]
                        result.append(f'<span style="color:{color}">')
                        current_style = code
                i = j + 1
            else:
                result.append(text[i])
                i += 1
        else:
            ch = text[i]
            if ch == '<':
                result.append('&lt;')
            elif ch == '>':
                result.append('&gt;')
            elif ch == '&':
                result.append('&amp;')
            else:
                result.append(ch)
            i += 1
    if current_style:
        result.append('</span>')
    return ''.join(result)


def mud_reader():
    global mud_socket
    buf = b''
    while True:
        try:
            data = mud_socket.recv(4096)
            if not data:
                socketio.emit('output', {'html': '<span style="color:#e74c3c">[Disconnected from server]</span>'})
                break
            buf += data
            text = buf.decode('latin-1', errors='replace')
            buf = b''
            # convert \r\n to \n, split on \n, emit each line
            text = text.replace('\r\n', '\n').replace('\r', '\n')
            html = ansi_to_html(text).replace('\n', '<br>')
            socketio.emit('output', {'html': html})
        except Exception as e:
            socketio.emit('output', {'html': f'<span style="color:#e74c3c">[Error: {e}]</span>'})
            break


def connect_to_mud():
    global mud_socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((MUD_HOST, MUD_PORT))
        mud_socket = s
        t = threading.Thread(target=mud_reader, daemon=True)
        t.start()
        return True
    except Exception as e:
        return False


@app.route('/')
def index():
    return render_template('index.html')


@socketio.on('connect')
def on_connect():
    global mud_socket
    if mud_socket is None:
        ok = connect_to_mud()
        if not ok:
            emit('output', {'html': '<span style="color:#e74c3c">[Could not connect to MUD on port 4000]</span>'})


@socketio.on('command')
def on_command(data):
    global mud_socket
    cmd = data.get('cmd', '')
    if mud_socket:
        try:
            mud_socket.sendall((cmd + '\r\n').encode('latin-1'))
        except Exception as e:
            emit('output', {'html': f'<span style="color:#e74c3c">[Send error: {e}]</span>'})


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=False, allow_unsafe_werkzeug=True)
