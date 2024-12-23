from flask import Flask, render_template
from flask_socketio import SocketIO, emit
import asyncio
import base64
import pyaudio
import dotenv
import os
from google import genai
import ffmpeg
import io
import wave

app = Flask(__name__)
socketio = SocketIO(app)

# Configure Gemini client
dotenv.load_dotenv()
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 512
MODEL = "models/gemini-2.0-flash-exp"
SYSTEM_PROMPT = "You are Rufous, the King of England."

client = genai.Client(
    http_options={"api_version": "v1alpha"},
    api_key=os.getenv("GOOGLE_API_KEY"),
)

CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "system_instruction": SYSTEM_PROMPT,
}


@app.route("/")
def index():
    return render_template("index.html")


@socketio.on("audio_data")
def handle_audio_data(data):
    audio_data = base64.b64decode(data.split(",")[1])

    def convert_webm_to_pcm(webm_data):
        input_stream = io.BytesIO(webm_data)

        # Convert webm to PCM using ffmpeg
        stream = ffmpeg.input("pipe:0", format="webm")
        stream = ffmpeg.output(
            stream,
            "pipe:1",
            format="s16le",  # 16-bit PCM
            acodec="pcm_s16le",
            ac=1,  # mono
            ar=16000,  # 16kHz sample rate
        )

        stdout, _ = ffmpeg.run(
            stream, input=input_stream.read(), capture_stdout=True, capture_stderr=True
        )
        return stdout

    def process_audio_wrapper():
        pcm_data = convert_webm_to_pcm(audio_data)

        # Create event loop for async operation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.set_debug(True)

        loop.run_until_complete(process_audio(pcm_data))
        loop.close()

    async def process_audio(audio_data):
        print("running process_audio")

        async with client.aio.live.connect(
            model=MODEL,
            config=CONFIG,
        ) as session:
            await session.send({"data": audio_data, "mime_type": "audio/pcm"})
            print("Audio sent")

            async for response in session.receive():
                if response.server_content:
                    model_turn = response.server_content.model_turn
                    if model_turn:
                        for part in model_turn.parts:
                            if part.inline_data:
                                # Convert single chunk to WAV and send immediately
                                wav_buffer = io.BytesIO()
                                with wave.open(wav_buffer, "wb") as wav_file:
                                    wav_file.setnchannels(1)
                                    wav_file.setsampwidth(2)
                                    wav_file.setframerate(24000)
                                    wav_file.writeframes(part.inline_data.data)

                                wav_data = wav_buffer.getvalue()
                                response_b64 = base64.b64encode(wav_data).decode(
                                    "utf-8"
                                )
                                socketio.emit("audio_chunk", response_b64)

    socketio.start_background_task(process_audio_wrapper)


if __name__ == "__main__":
    socketio.run(app, port=3000)
