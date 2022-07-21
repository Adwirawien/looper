import pyaudio
import time
import wave
import numpy
import multiprocessing

CHUNK = 1
FORMAT = pyaudio.paInt32
CHANNELS = 2
RATE = 48000
WAVE_OUTPUT_FILENAME = "loop_x.wav"

p = pyaudio.PyAudio()
recording = False

stream_buffer = []
tapes = []
def toggle_recording():
    global recording, stream_buffer, wf, tapes
    if recording:
        recording = False
        name = WAVE_OUTPUT_FILENAME.replace("x", str(len(tapes)+1))
        wf = wave.open(name, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(stream_buffer))
        wf.close()
        tapes.append(wave.open(name, 'rb'))
        print(" * Stopped recording")
    else:
        recording = True
        print(" * Started recording")
        stream_buffer = []

def reset_recording():
    global recording, stream_buffer, tapes
    print(" * Resetting recording")
    recording = False
    for t in tapes:
        t.close()
    tapes = []
    stream_buffer = []

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
            toggle_recording()
        else:
            timer = 0
        last_state = state
    else:
        if timer == threshold and state:
            reset_recording()
        timer += 1

stream_data = None
def callback(in_data, frame_count, time_info, status):
    global recording, stream_buffer, wf, stream_data

    out_data = in_data
    stream_data = in_data

    if (recording):
        stream_buffer.append(in_data)
    if len(tapes) > 0:
        rec_mix = None

        played_count = 0
        for tape in tapes:
            if hasattr(tape, 'readframes'):
                sound = tape.readframes(frame_count)
                if (sound == b''):
                    played_count+=1
                soundarray = numpy.frombuffer(sound, dtype=numpy.int32)

                if rec_mix is None:
                    rec_mix = soundarray
                else:
                    if rec_mix.shape == (0,):
                        rec_mix = (soundarray).astype(dtype=numpy.int32)
                    elif soundarray.shape == (0,):
                        rec_mix = (rec_mix).astype(dtype=numpy.int32)
                    else:
                        rec_mix = (rec_mix + soundarray).astype(dtype=numpy.int32)
        if (played_count >= len(tapes)):
            for tape in tapes:
                tape.rewind()
                    
        in_mix = numpy.frombuffer(in_data, dtype=numpy.int32)
        if rec_mix.shape == (0,):
            out_data = (in_mix).astype(dtype=numpy.int32).tobytes()
        else:
            out_data = (in_mix + rec_mix).astype(dtype=numpy.int32).tobytes()

    return (out_data, pyaudio.paContinue)

stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                output=True,
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

