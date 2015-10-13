from socketIO_client import SocketIO, LoggingNamespace
import json
import base64

def on_data(data):
    audio_data = data['audio']
    spectrum_data = data['fft']
    num_samples = data['samples']
    output.write(base64.b64decode(audio_data))

def on_connect(*args):
    pass

def on_disconnect(*args):
    pass
