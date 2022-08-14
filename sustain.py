import pyaudio
import time
import numpy
from pynput.keyboard import Key, Controller
keyboard = Controller()

CHUNK = 1
FORMAT = pyaudio.paInt16
CHANNELS = 2
RATE = 48000

p = pyaudio.PyAudio()

last_samples = []
last_state = False
timer = 0
def pedal_loop(in_data):
    global last_samples, last_state, timer, cooldown

    pedal = round(abs(numpy.frombuffer(in_data, dtype=numpy.int32)[1]/100000000))
    # create an average of the last 1000 pedal samples
    avg = 0
    last_samples.append(pedal)
    # if we have more than 1000 samples, remove the first one
    if len(last_samples) > 100:
        last_samples.pop(0)
    # calculate the average
    for i in last_samples:
        avg += i
    avg /= len(last_samples)

    # the following applies:
    # avg goes from 0 to >0.5 to 0 in a short period of time -> toggle recording
    # avg goes from 0 to >0.5 to 0 in a long period of time -> reset recording
    # avg stays at 0 -> do nothing
    # for every state, the event should only be triggered once
    
    if avg > 0.5:
        state = True
    else:
        state = False
    
    threshold = 1000
    if state != last_state:
        if state:
            timer = 0
            keyboard.press(Key.space)
            keyboard.release(Key.space)
        else:
            timer = 0
        last_state = state
    else:
        if timer == threshold and state:
            keyboard.press(Key.enter)
            keyboard.release(Key.enter)
        timer += 1

stream_data = None
def callback(in_data, frame_count, time_info, status):
    global stream_data

    stream_data = in_data

    return (None, pyaudio.paContinue)

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=False,
                frames_per_buffer=CHUNK,
                stream_callback=callback)

print("* starting")

stream.start_stream()
try:
    while stream.is_active():
        if (stream_data is not None):
            pedal_loop(stream_data)
        time.sleep(1/1000)
except KeyboardInterrupt:
    pass

print("* stopping")
stream.stop_stream()
stream.close()

p.terminate()

