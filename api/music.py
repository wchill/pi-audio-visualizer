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
    return ''.join(buf2) + ''.join(buf)


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
    frames_played = 0

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

        yield output, frames_played, update_lights(matrix, mean, std)

        # Read next chunk of data from music song_filename
        data = music_file.readframes(CHUNK_SIZE)
        row += 1

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


if __name__ == "__main__":
    play_song('sample.mp3')
