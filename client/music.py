#!/usr/bin/env python

import alsaaudio as aa

import Adafruit_CharLCD as LCD

CHUNK_SIZE = 2048
NUM_CHANNELS = 20

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


def update_display(spectrum, frames_played, total_frames, sample_rate):
    lcd.set_cursor(0,3)
    lcd.message(spectrum[:NUM_CHANNELS])
    lcd.set_cursor(0,2)
    lcd.message(spectrum[NUM_CHANNELS:])

    total_seconds = total_frames / sample_rate
    m, s = divmod(total_seconds, 60)
    total_time = "%d:%02d" % (m,s)

	seconds = frames_played / sample_rate
    m, s = divmod(seconds, 60)
    time = "%d:%02d" % (m, s)

    lcd.set_cursor(0,0)
	lcd.message('Now playing\n{}/{}'.format(time, total_time))


def init(num_channels, sample_rate)
    output.setchannels(num_channels)
    output.setrate(sample_rate)
    output.setformat(aa.PCM_FORMAT_S16_LE)
    output.setperiodsize(CHUNK_SIZE)


class PushNamespace(BaseNamespace):

    def on_connect(self, *args):
        print('Connected!')

    def on_ready(self, data):
        print('Ready to play')
        init(data['channels'], data['rate'])
        self.emit('getdata')

    def on_data(data):
        audio_data = data['audio']
        spectrum_data = data['spectrum']
        frames_played = data['frames']
        total_frames = data['total']
        sample_rate = data['rate']
        output.write(base64.b64decode(audio_data))
        update_display(spectrum_data, frames_played, total_frames, sample_rate) 
        self.emit('getdata')

    def on_disconnect(self, *args):
        print('Disconnected!')

socketIO = SocketIO('http://intense.io/push', 9001)
socketIO.wait()
