# Core-4 Drive

A smart car prototype in two parts: a real robot car that can recognise its driver's face and drive itself, and an in-car cockpit dashboard with a voice AI assistant called Neuro.

## Parts

### [`car/`](car/): the robot car

- **Arduino UNO R4 WiFi** (`arduino_firmware/`): motors through a TB6612FNG driver, ultrasonic and IR obstacle sensors, speed sensor, buzzer, emergency stop button, GY-87 IMU and motor battery reading.
- **Raspberry Pi 4 + Pi Camera** (`pi_server/`): a FastAPI server with a web control page, live camera stream, face registration and verification to unlock the car, AI driving modes (roaming, auto parking with ArUco markers), an event history in SQLite, and battery monitoring. The Pi talks to the Arduino over USB serial.
- `docs/` has the wiring diagram, servo notes and test order. `tools/make_aruco_marker.py` prints the parking markers.

Run the server on the Pi:

```bash
cd car/pi_server
python -m venv venv && . venv/bin/activate
pip install -r requirements.txt
python main.py
```

See [car/README_VI.md](car/README_VI.md) (Vietnamese) for wiring and power safety notes.

### [`dashboard/`](dashboard/): the cockpit dashboard

A PyQt5 desktop app with a dark three-panel layout: vehicle status gauges, a chat with the Neuro assistant, and a real map.

- **Neuro assistant**: "Hey Neuro" wake word, speech recognition and text to speech. Answers come from an offline-first chain: built-in modules first, then a local Ollama model, then Claude when an `ANTHROPIC_API_KEY` is set.
- **Real data**: OpenStreetMap map, place search, OSRM road routing and Open-Meteo weather.
- **Simulated data** for the demo: speed, fuel, battery and hazard alerts.
- Learns the driver's habits to improve its suggestions.

Run on Windows:

```powershell
cd dashboard
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

See [dashboard/README.md](dashboard/README.md) (Japanese) for the full feature list, AI modules and controls.

## Privacy

Face images, the face database, the event log, the learned habits file and any saved API key are created at runtime and are not stored in this repository.
