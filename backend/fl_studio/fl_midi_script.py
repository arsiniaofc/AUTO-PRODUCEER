"""FL Studio Official MIDI Script Generator (Layer A - Structured Integration).
Generates the Python script and configuration needed by FL Studio's MIDI Scripting engine.
"""
import os

FL_SCRIPT_TEMPLATE = '''# name=Autonomous Music Producer Bridge
# url=http://127.0.0.1:8000
"""
FL Studio MIDI Controller Script for Autonomous Music Producer.
Place this script in:
Documents/Image-Line/FL Studio/Settings/Hardware/AutonomousProducer/device_AutonomousProducer.py
"""

import transport
import channels
import patterns
import playlist
import mixer
import general
import ui
import midi

print("[Autonomous Music Producer] Bridge Controller Script Inicializado no FL Studio!")

# Command Mapping via MIDI CC
CC_PLAY = 20
CC_STOP = 21
CC_RECORD = 22
CC_TEMPO_UP = 23
CC_TEMPO_DOWN = 24
CC_NEXT_PATTERN = 25
CC_PREV_PATTERN = 26
CC_SELECT_CHANNEL = 27
CC_ADD_PATTERN = 28
CC_OPEN_PIANO_ROLL = 29
CC_EMERGENCY_STOP = 30

def OnInit():
    print("[Autonomous Producer] Conexao estabelecida com a DAW.")

def OnDeInit():
    print("[Autonomous Producer] Conexao finalizada.")

def OnMidiMsg(event):
    if event.status == midi.MIDI_CONTROLCHANGE:
        cc = event.data1
        val = event.data2

        if cc == CC_PLAY and val > 0:
            transport.start()
            event.handled = True
        elif cc == CC_STOP and val > 0:
            transport.stop()
            event.handled = True
        elif cc == CC_RECORD and val > 0:
            transport.record()
            event.handled = True
        elif cc == CC_NEXT_PATTERN and val > 0:
            patterns.findFirstNext(1)
            event.handled = True
        elif cc == CC_PREV_PATTERN and val > 0:
            patterns.findFirstNext(-1)
            event.handled = True
        elif cc == CC_OPEN_PIANO_ROLL and val > 0:
            ui.showWindow(midi.widPianoRoll)
            event.handled = True
        elif cc == CC_EMERGENCY_STOP:
            transport.stop()
            general.undo()
            event.handled = True
'''


def generate_fl_midi_script(output_dir: str = "data/fl_studio_script") -> str:
    """Generates the ready-to-use FL Studio Python MIDI Script."""
    os.makedirs(output_dir, exist_ok=True)
    script_path = os.path.join(output_dir, "device_AutonomousProducer.py")
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(FL_SCRIPT_TEMPLATE)
    return script_path
