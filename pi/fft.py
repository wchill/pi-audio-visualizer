#
# Licensed under the BSD license.  See full license in LICENSE file.
# http://www.lightshowpi.com/
#
# Author: Todd Giles (todd@lightshowpi.com)

"""FFT methods for computing / analyzing frequency response of audio.

This is simply a wrapper around FFT support in numpy.

Initial FFT code inspired from the code posted here:
http://www.raspberrypi.org/phpBB3/viewtopic.php?t=35838&p=454041

Optimizations from work by Scott Driscoll:
http://www.instructables.com/id/Raspberry-Pi-Spectrum-Analyzer-with-RGB-LED-Strip-/

Third party dependencies:

numpy: for FFT calculation - http://www.numpy.org/
"""
from numpy import sum as npsum
from numpy import abs as npabs
from numpy import log10, frombuffer, empty, hanning, fft, delete, int16, zeros
from pylru import lrudecorator


@lrudecorator(100)
def cached_hanning(size):
    return hanning(size)


def calculate_levels(data, chunk_size, sample_rate, frequency_limits, num_bins, input_channels=2):
    """Calculate frequency response for each channel defined in frequency_limits

    :param data: decoder.frames(), audio data for fft calculations
    :type data: decoder.frames

    :param chunk_size: chunk size of audio data
    :type chunk_size: int

    :param sample_rate: audio file sample rate
    :type sample_rate: int

    :param frequency_limits: list of frequency_limits
    :type frequency_limits: list

    :param num_bins: length of gpio to process
    :type num_bins: int

    :param input_channels: number of audio input channels to process for (default=2)
    :type input_channels: int

    :return:
    :rtype: numpy.array
    """

    # create a numpy array, taking just the left channel if stereo
    data_stereo = frombuffer(data, dtype=int16)
    if input_channels == 2:
        # data has 2 bytes per channel
        data = empty(len(data) / (2 * input_channels))

        # pull out the even values, just using left channel
        data[:] = data_stereo[::2]
    elif input_channels == 1:
        data = data_stereo

    # if you take an FFT of a chunk of audio, the edges will look like
    # super high frequency cutoffs. Applying a window tapers the edges
    # of each end of the chunk down to zero.
    data = data * cached_hanning(len(data))

    # Apply FFT - real data
    fourier = fft.rfft(data)

    # Remove last element in array to make it the same size as chunk_size
    fourier = delete(fourier, len(fourier) - 1)

    # Calculate the power spectrum
    power = npabs(fourier) ** 2

    matrix = zeros(num_bins, dtype='float64')
    for pin in range(num_bins):
        # take the log10 of the resulting sum to approximate how human ears
        # perceive sound levels

        # Get the power array index corresponding to a particular frequency.
        idx1 = int(chunk_size * frequency_limits[pin][0] / sample_r
