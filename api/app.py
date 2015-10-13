from flask import Flask, request, jsonify
from youtube_dl import YoutubeDL
from flask.ext.socketio import SocketIO, emit
import base64

app = Flask(__name__)
socketio = SocketIO(app)
f_buffer = None
with open('audio/sample.mp3', 'rb') as f:
    f_buffer = f.read()

@app.route('/next-track')
def next_track():
    return send_file('audio/sample.mp3')

@socketio.on('connect', namespace='/push')
def connect():
    print 'Client connected'

@socketio.on('getdata', namespace='/push')
def send_data():
    socketio.emit('data', {'audio': 

@socketio.on('disconnect', namespace='/push')
def disconnect():
    print 'Client disconnected'

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8081)
