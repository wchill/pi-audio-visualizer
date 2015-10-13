#!/usr/bin/env python

import atexit
import os
import random
import subprocess
import sys
import wave
import alsaaudio as aa

import decoder
import numpy as np

import fft

import Adafruit_CharLCD as LCD

_MIN_FREQUENCY = 20
_MAX_FREQUENCY = 10000

_CUSTOM_CHANNEL_FREQUENCIES = 0
_CUSTOM_CHANNEL_MAPPING = 0

CHUNK_SIZE = 2048
NUM_CHANNELS = 20


def end_early():
    # hc.clean_up()
    pass


atexit.register(end_early)


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

# Use HSV color space so the hue can be adjusted to see a nice gradient of colors.
# Hue ranges from 0.0 to 359.0, saturation from 0.0 to 1.0, and value from 0.0 to 1.0.
hue = 0.0
saturation = 1.0
value = 1.0

lcd.create_char(0, [0,0,0,0,0,0,0,31])
lcd.create_char(1, [0,0,0,0,0,0,31,31])
lcd.create_char(2, [0,0,0,0,0,31,31,31])
lcd.create_char(3, [0,0,0,0,31,31,31,31])
lcd.create_char(4, [0,0,0,31,31,31,31,31])
lcd.create_char(5, [0,0,31,31,31,31,31,31])
lcd.create_char(6, [0,31,31,31,31,31,31,31])
lcd.create_char(7, [31,31,31,31,31,31,31,31])
lcd.clear()


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


def update_lights(matrix, mean, std):
    """Update the state of all the lights

    Update the state of all the lights based upon the current
    frequency response matrix

    :param matrix: row of data from cache matrix
    :type matrix: list

    :param mean: standard mean of fft values
    :type mean: list

    :param std: standard deviation of fft values
    :type std: list
    """
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


def play_song(song_filename):

    # Initialize Lights
    # hc.initialize()

    # Ensure play_now is reset before beginning playback

    # Set up audio
    if song_filename.endswith('.wav'):
        music_file = wave.open(song_filename, 'r')
    else:
        music_file = decoder.open(song_filename)

    sample_rate = music_file.getframerate()
    num_channels = music_file.getnchannels()
    output = aa.PCM(aa.PCM_PLAYBACK, aa.PCM_NORMAL)
    output.setchannels(num_channels)
    output.setrate(sample_rate)
    output.setformat(aa.PCM_FORMAT_S16_LE)
    output.setperiodsize(CHUNK_SIZE)

    print("Playing: " + song_filename + " (" + str(music_file.getnframes() / sample_rate)
                 + " sec)")

    # Output a bit about what we're about to play to the logs
    song_filename = os.path.abspath(song_filename)

    # create empty array for the cache_matrix
    cache_matrix = np.empty(shape=[0, NUM_CHANNELS])
    cache_found = False
    cache_filename = os.path.dirname(song_filename) + \
        "/." + os.path.basename(song_filename) + ".sync"
    print cache_filename

    # The values 12 and 1.5 are good estimates for first time playing back
    # (i.e. before we have the actual mean and standard deviations
    # calculated for each channel).
    mean = [12.0 for _ in range(NUM_CHANNELS)]
    std = [1.5 for _ in range(NUM_CHANNELS)]

    # Read in cached fft
    try:
        # load cache from file using numpy loadtxt
        cache_matrix = np.loadtxt(cache_filename)
        cache_found = True

        # get std from matrix / located at index 0
        std = np.array(cache_matrix[0])

        # get mean from matrix / located at index 1
        mean = np.array(cache_matrix[1])

        # delete mean and std from the array
        cache_matrix = np.delete(cache_matrix, 0, axis=0)
        cache_matrix = np.delete(cache_matrix, 0, axis=0)

        print("std: " + str(std) + ", mean: " + str(mean))
    except IOError:
        print("Cached sync data song_filename not found: '"
                     + cache_filename
                     + "'.  One will be generated.")

    # Process audio song_filename
    row = 0
    data = music_file.readframes(CHUNK_SIZE)
    frequency_limits = calculate_channel_frequency(_MIN_FREQUENCY, _MAX_FREQUENCY)

    # timer
    total_seconds = music_file.getnframes() / sample_rate
    m, s = divmod(total_seconds, 60)
    total_time = "%d:%02d" % (m,s)
    frames_played = 0
    update_rate = sample_rate / 10
    last_update_display = 0
    last_update_spec = 0

    while data != '':
        output.write(data)

        # Control lights with cached timing values if they exist
        matrix = None
        if cache_found and args.readcache:
            if row < len(cache_matrix):
                matrix = cache_matrix[row]
            else:
                print("Ran out of cached FFT values, will update the cache.")
                cache_found = False

        if matrix is None:
            # No cache - Compute FFT in this chunk, and cache results
            matrix = fft.calculate_levels(data, CHUNK_SIZE, sample_rate, frequency_limits,
                                          NUM_CHANNELS)

            # Add the matrix to the end of the cache
            cache_matrix = np.vstack([cache_matrix, matrix])

        frames_played += len(data) / 4
        if last_update_display + sample_rate < frames_played:
	    seconds = frames_played / sample_rate
            m, s = divmod(seconds, 60)
            lcd.set_cursor(0,0)
	    lcd.message('Now playing\n{}/{}'.format("%d:%02d" % (m, s), total_time))
            last_update_display = frames_played

        if last_update_spec + update_rate < frames_played:
            update_lights(matrix, mean, std)
            last_update_spec = frames_played

        # Read next chunk of data from music song_filename
        data = music_file.readframes(CHUNK_SIZE)
        row += 1

        # Load new application state in case we've been interrupted
        # cm.load_state()
        # play_now = int(cm.get_state('play_now', "0"))

    if not cache_found:
        # Compute the standard deviation and mean values for the cache
        for i in range(0, NUM_CHANNELS):
            std[i] = np.std([item for item in cache_matrix[:, i] if item > 0])
            mean[i] = np.mean([item for item in cache_matrix[:, i] if item > 0])

        # Add mean and std to the top of the cache
        cache_matrix = np.vstack([mean, cache_matrix])
        cache_matrix = np.vstack([std, cache_matrix])

        # Save the cache using numpy savetxt
        np.savetxt(cache_filename, cache_matrix)

        print("Cached sync data written to '." + cache_filename
                     + "' [" + str(len(cache_matrix)) + " rows]")

    # check for postshow
    # PrePostShow('postshow', hc).execute()

    # We're done, turn it all off and clean up things ;)
    # hc.clean_up()


if __name__ == "__main__":
    play_song('sample.mp3')
