#!/usr/bin/env python

import alsaaudio as aa
from socketIO_client import SocketIO, BaseNamespace
import base64
import requests
import json
import decoder
import os.path
import re
import numpy as np

import Adafruit_CharLCD as LCD

CHUNK_SIZE = 2048
NUM_CHANNELS = 20
_MIN_FREQUENCY = 20
_MAX_FREQUENCY = 15000

# Raspberry Pi configuration:
lcd_rs = 25  # Change this to pin 21 on older revision Raspberry Pi's
lcd_en = 24
lcd_d4 = 23
lcd_d5 = 18
lcd_d6 = 15
lcd_d7 = 14
lcd_red   = 21
lcd_green = 20
lcd_blue  = 16

# Alternatively specify a 20x4 LCD.
lcd_columns = 20
lcd_rows    = 4

# Initialize the LCD using the pins
lcd = LCD.Adafruit_RGBCharLCD(lcd_rs, lcd_en, lcd_d4, lcd_d5, lcd_d6, lcd_d7,
                                lcd_columns, lcd_rows, lcd_red, lcd_green, lcd_blue,
                                enable_pwm=True)

lcd.create_char(0, [0,0,0,0,0,0,0,31])
lcd.create_char(1, [0,0,0,0,0,0,31,31])
lcd.create_char(2, [0,0,0,0,0,31,31,31])
lcd.create_char(3, [0,0,0,0,31,31,31,31])
lcd.create_char(4, [0,0,0,31,31,31,31,31])
lcd.create_char(5, [0,0,31,31,31,31,31,31])
lcd.create_char(6, [0,31,31,31,31,31,31,31])
lcd.create_char(7, [31,31,31,31,31,31,31,31])
lcd.clear()

output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)

def calculate_channel_frequency(min_frequency, max_frequency):

    channel_length = NUM_CHANNELS

    print("Calculating frequencies for %d channels.", channel_length)
    octaves = (np.log(max_frequency / min_frequency)) / np.log(2)
    print("octaves in selected frequency range ... %s", octaves)
    octaves_per_channel = octaves / channel_length
    frequency_limits = []
    frequency_store = []

    frequency_limits.append(min_frequency)

    for pin in range(1, NUM_CHANNELS + 1):
        frequency_limits.append(frequency_limits[-1] * 10 ** (3 / (10 * (1 / octaves_per_channel))))
    for pin in range(0, channel_length):
        frequency_store.append((frequency_limits[pin], frequency_limits[pin + 1]))
        print("channel %d is %6.2f to %6.2f ", pin, frequency_limits[pin],
                      frequency_limits[pin + 1])

    return frequency_store


def update_display(matrix, mean, std, frames_played, sample_rate, total_time):
    buf = [chr(32) for x in xrange(NUM_CHANNELS)]
    buf2 = [chr(32) for x in xrange(NUM_CHANNELS)]
    for pin in range(0, NUM_CHANNELS):
        # Calculate output pwm, where off is at some portion of the std below
        # the mean and full on is at some portion of the std above the mean.
        brightness = matrix[pin] - mean[pin] + 0.5 * std[pin]
        brightness /= 1.25 * std[pin]
        brightness = int(16 * brightness)
        if brightness > 16:
            brightness = 16

        if brightness < 0:
            brightness = 0

        if brightness >= 8:
            buf[pin] = chr(brightness - 8)
            buf2[pin] = chr(7)
        else:
            buf2[pin] = chr(brightness)
    lcd.set_cursor(0,3)
    lcd.message(''.join(buf2))
    lcd.set_cursor(0,2)
    lcd.message(''.join(buf))


def init(num_channels, sample_rate):
    print('channels: {}, rate: {}'.format(num_channels, sample_rate))
    output.setchannels(num_channels)
    output.setrate(sample_rate)
    output.setformat(aa.PCM_FORMAT_S16_LE)
    output.setperiodsize(CHUNK_SIZE)


def download_file(url):
    # NOTE the stream=True parameter
    r = requests.get(url, stream=True)
    d = r.headers['Content-Disposition']
    filename = re.findall("filename=(.+)", d)[0]
    if os.path.isfile(filename):
        r.connection.close()
        return filename
    with open(filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=4096): 
            if chunk: # filter out keep-alive new chunks
                f.write(chunk)
    return filename

song_filename = download_file('http://intense.io:9001/get-track')
cache_filename = download_file('http://intense.io:9001/get-fft')
music_file = decoder.open(song_filename)
num_channels = music_file.getnchannels()
sample_rate = music_file.getframerate()
init(num_channels, sample_rate)

# load cache from file using numpy loadtxt
cache_matrix = np.loadtxt(cache_filename)

# get std from matrix / located at index 0
std = np.array(cache_matrix[0])

# get mean from matrix / located at index 1
mean = np.array(cache_matrix[1])

# delete mean and std from the array
cache_matrix = np.delete(cache_matrix, 0, axis=0)

print("std: " + str(std) + ", mean: " + str(mean))

# Process audio song_filename
row = 0
data = music_file.readframes(CHUNK_SIZE)
frequency_limits = calculate_channel_frequency(_MIN_FREQUENCY, _MAX_FREQUENCY)

# timer
total_seconds = music_file.getnframes() / sample_rate
m, s = divmod(total_seconds, 60)
total_time = "%d:%02d" % (m,s)
sample_rate *= 4
update_rate = sample_rate / 8
frames_played = 0
last_update_display = 0
last_update_spec = 0

while data != '':
    output.write(data)

    # Control lights with cached timing values if they exist

    frames_played += len(data)
    if last_update_display + sample_rate < frames_played:
        seconds = frames_played / sample_rate
        m, s = divmod(seconds, 60)
        lcd.set_cursor(0,0)
        lcd.message('Now playing\n{}/{}'.format("%d:%02d" % (m, s), total_time))
        last_update_display = frames_played

    if last_update_spec + update_rate < frames_played:
        update_display(cache_matrix[row], mean, std, frames_played, sample_rate, total_time)
        last_update_spec = frames_played

    # Read next chunk of data from music song_filename
    data = music_file.readframes(CHUNK_SIZE)
    row += 1

"""
class PushNamespace(BaseNamespace):

    def on_connect(self, *args):
        print('Connected!')

    def on_ready(self, data):
        print('Ready to play')
        init(data['channels'], data['rate'])
        self.emit('getdata')

    def on_data(self, data):
        audio_data = data['audio']
        spectrum_data = data['spectrum']
        frames_played = data['frames']
        total_frames = data['total']
        sample_rate = data['rate']
        output.write(base64.b64decode(audio_data))
        print frames_played
        update_display(base64.b64decode(spectrum_data), frames_played, total_frames, sample_rate) 
        self.emit('getdata')

    def on_disconnect(self, *args):
        print('Disconnected!')

socketIO = SocketIO('http://intense.io', 9001)
push_namespace = socketIO.define(PushNamespace, '/push')
push_namespace.emit('connect')
socketIO.wait()
"""
