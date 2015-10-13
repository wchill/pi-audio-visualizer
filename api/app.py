from flask import Flask, request, jsonify
from youtube_dl import YoutubeDL
from flask.ext.socketio import SocketIO, emit
import base64

app = Flask(__name__)
socketio = SocketIO(app)
audio_gen = None
with open('audio/sample.mp3', 'rb') as f:
    f_buffer = f.read()

@app.route('/next-track')
def next_track():
    return send_file('audio/sample.mp3')

@socketio.on('connect', namespace='/push')
def connect():
    print 'Client connected'
    new_song('audio/sample.mp3')
    num_channels, sample_rate = audio_gen.next()
    socketio.emit('ready', {'channels': num_channels, 'rate': sample_rate}, namespace='/push')

@socketio.on('getdata', namespace='/push')
def send_data():
    try:
	output, frames, total_frames, sample_rate, spectrum = audio_gen.next()
	socketio.emit('data', {'audio': base64.b64encode(output), 'spectrum': base64.b64encode(spectrum), 'frames': frames, 'total': total, 'rate': sample_rate}, namespace='/push')
    except StopIteration:
        new_song('audio/sample.mp3')

@socketio.on('disconnect', namespace='/push')
def disconnect():
    print 'Client disconnected'

def new_song(filename):
    audio_gen = play_song(filename)
    num_channels, sample_rate = audio_gen.next()
    socketio.emit('ready', {'channels': num_channels, 'rate': sample_rate}, namespace='/push')


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8081)
