# Copyright 2026 Google LLC
# Media generators for toddler vehicles: animated GIFs and audio clips (WAV)

import io
import math
import struct
import wave
from PIL import Image, ImageDraw


def generate_vehicle_wav(vehicle_type: str) -> bytes:
    """Synthesizes a short, recognizable audio WAV sound clip for a vehicle."""
    sample_rate = 22050
    v = vehicle_type.lower()
    
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        if "fire" in v or "siren" in v:
            # Alternating emergency siren (wee-woo)
            duration = 2.0
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                freq = 750 + 200 * math.sin(2 * math.pi * 2.0 * t)
                val = int(18000 * math.sin(2 * math.pi * freq * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        elif "train" in v:
            # Train whistle (dual chord 523Hz + 659Hz + 784Hz)
            duration = 2.2
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                envelope = 1.0 if (0.1 < t < 0.9 or 1.1 < t < 2.0) else 0.05
                val = int(envelope * 8000 * (
                    math.sin(2 * math.pi * 523 * t) +
                    math.sin(2 * math.pi * 659 * t) +
                    math.sin(2 * math.pi * 784 * t)
                ))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        elif "race" in v or "sport" in v:
            # Race car revving: pitch glide upwards
            duration = 1.8
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                freq = 120 + 400 * (t / duration) ** 2
                val = int(18000 * math.sin(2 * math.pi * freq * t))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        elif "dump" in v or "garbage" in v:
            # Reverse warning beeper: 1000Hz intermittent beeps
            duration = 2.0
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                in_beep = (int(t * 4) % 2 == 0)
                val = int(16000 * math.sin(2 * math.pi * 1000 * t)) if in_beep else 0
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        elif "tractor" in v or "excavator" in v or "bulldozer" in v or "construction" in v:
            # Low diesel engine chug-chug
            duration = 2.0
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                chug_env = 0.5 + 0.5 * math.sin(2 * math.pi * 6 * t)
                val = int(chug_env * 16000 * (
                    math.sin(2 * math.pi * 75 * t) +
                    0.5 * math.sin(2 * math.pi * 150 * t)
                ))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        else:
            # Classic friendly car / truck horn: "Beep beep!"
            duration = 1.5
            num_samples = int(duration * sample_rate)
            for i in range(num_samples):
                t = i / sample_rate
                envelope = 1.0 if (0.1 < t < 0.45 or 0.6 < t < 0.95) else 0.0
                val = int(envelope * 12000 * (
                    math.sin(2 * math.pi * 440 * t) +
                    math.sin(2 * math.pi * 554 * t)
                ))
                frames.extend(struct.pack("<h", max(-32767, min(32767, val))))

        wav_file.writeframes(frames)

    return buf.getvalue()


def generate_vehicle_gif(vehicle_type: str) -> bytes:
    """Generates a bright, colorful animated looping GIF of the vehicle moving."""
    v = vehicle_type.lower()
    width, height = 360, 200
    num_frames = 12
    frames = []

    if "fire" in v:
        v_color = "#E53935"
        title = "🚒 Fire Engine"
        is_emergency = True
    elif "dump" in v:
        v_color = "#FDD835"
        title = "🚛 Dump Truck"
        is_emergency = False
    elif "garbage" in v or "trash" in v:
        v_color = "#43A047"
        title = "♻️ Garbage Truck"
        is_emergency = False
    elif "excavator" in v or "digger" in v:
        v_color = "#FB8C00"
        title = "🚜 Excavator"
        is_emergency = False
    elif "tractor" in v:
        v_color = "#2E7D32"
        title = "🚜 Tractor"
        is_emergency = False
    elif "police" in v:
        v_color = "#1E88E5"
        title = "🚓 Police Car"
        is_emergency = True
    elif "race" in v:
        v_color = "#D81B60"
        title = "🏎️ Race Car"
        is_emergency = False
    elif "train" in v:
        v_color = "#5E35B1"
        title = "🚂 Train"
        is_emergency = False
    else:
        v_color = "#039BE5"
        title = "🚗 Cool Truck"
        is_emergency = False

    for f in range(num_frames):
        img = Image.new("RGB", (width, height), "#81D4FA")
        draw = ImageDraw.Draw(img)

        # Green hill ground & road
        draw.rectangle([0, 140, width, height], fill="#7CB342")
        draw.rectangle([0, 155, width, 185], fill="#424242")

        # Moving road dashes
        dash_offset = (f * 8) % 30
        for x_dash in range(-30 + dash_offset, width + 30, 30):
            draw.line([x_dash, 170, x_dash + 14, 170], fill="#FFFFFF", width=3)

        # Vehicle bounce animation
        bounce = int(3 * math.sin(f * (2 * math.pi / num_frames)))
        vx = 70 + int(10 * math.cos(f * (2 * math.pi / num_frames)))
        vy = 90 + bounce

        # Vehicle Body
        draw.rounded_rectangle([vx, vy, vx + 160, vy + 55], radius=8, fill=v_color, outline="#212121", width=3)

        # Vehicle Cab / Windows
        draw.rounded_rectangle([vx + 100, vy - 20, vx + 155, vy + 30], radius=6, fill=v_color, outline="#212121", width=3)
        draw.rectangle([vx + 115, vy - 15, vx + 150, vy + 10], fill="#E0F7FA", outline="#212121", width=2)

        # Emergency Siren (Flashing)
        if is_emergency:
            siren_color = "#FF1744" if (f % 4 < 2) else "#00E5FF"
            draw.ellipse([vx + 125, vy - 32, vx + 142, vy - 21], fill=siren_color, outline="#212121", width=2)
            if f % 2 == 0:
                draw.line([vx + 120, vy - 36, vx + 112, vy - 42], fill="#FFEB3B", width=2)
                draw.line([vx + 147, vy - 36, vx + 155, vy - 42], fill="#FFEB3B", width=2)

        # Headlight
        draw.polygon([(vx + 160, vy + 20), (vx + 215, vy + 8), (vx + 215, vy + 42)], fill="#FFF9C4")
        draw.ellipse([vx + 154, vy + 18, vx + 162, vy + 32], fill="#FFD600", outline="#212121", width=2)

        # Rotating Wheels
        wheel_radius = 18
        wheel_positions = [(vx + 35, vy + 55), (vx + 130, vy + 55)]
        for wx, wy in wheel_positions:
            draw.ellipse([wx - wheel_radius, wy - wheel_radius, wx + wheel_radius, wy + wheel_radius], fill="#212121", outline="#424242", width=2)
            draw.ellipse([wx - 8, wy - 8, wx + 8, wy + 8], fill="#B0BEC5", outline="#37474F", width=1)
            angle = f * (2 * math.pi / num_frames) * 2
            dx = int(8 * math.cos(angle))
            dy = int(8 * math.sin(angle))
            draw.line([wx - dx, wy - dy, wx + dx, wy + dy], fill="#ECEFF1", width=2)

        # Cloud & Sun
        draw.ellipse([20, 20, 70, 45], fill="#FFFFFF")
        draw.ellipse([45, 12, 90, 42], fill="#FFFFFF")
        draw.ellipse([70, 20, 115, 45], fill="#FFFFFF")
        draw.ellipse([290, 15, 340, 65], fill="#FFD54F", outline="#FFA000", width=2)

        frames.append(img)

    buf = io.BytesIO()
    frames[0].save(
        buf,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=120,
        loop=0,
    )
    return buf.getvalue()
