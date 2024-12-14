# Adapted from https://github.com/google-gemini/cookbook/blob/8495ce7619235d9a6c6478114cf69a077d73fdf4/gemini-2/live_api_starter.py
# License: Apache 2.0

import asyncio
import sys
import traceback
import pyaudio
import dotenv
import os
from google import genai

FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 512

MODEL = "models/gemini-2.0-flash-exp"

SYSTEM_PROMPT = "You are Rufous, the King of England."

dotenv.load_dotenv()

client = genai.Client(
    http_options={"api_version": "v1alpha"},
    api_key=os.getenv("GOOGLE_API_KEY"),
)

CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"]},
    "system_instruction": SYSTEM_PROMPT,
}

pya = pyaudio.PyAudio()


class AudioLoop:
    def __init__(self):
        self.audio_in_queue = asyncio.Queue()
        self.audio_out_queue = asyncio.Queue()

        self.session = None

        self.send_text_task = None
        self.receive_audio_task = None
        self.play_audio_task = None

    async def send_text(self):
        while True:
            text = await asyncio.to_thread(input, "message > ")
            if text.lower() == "q":
                break
            await self.session.send(text or ".", end_of_turn=True)

    async def record_audio(self):
        pya = pyaudio.PyAudio()

        mic_info = pya.get_default_input_device_info()
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=SEND_SAMPLE_RATE,
            input=True,
            input_device_index=mic_info["index"],
            frames_per_buffer=CHUNK_SIZE,
        )

        while True:
            data = await asyncio.to_thread(stream.read, CHUNK_SIZE)

            # If the audio_in_queue is empty then we will send audio out, otherwise discard the audio
            if self.audio_in_queue.empty():
                self.audio_out_queue.put_nowait(data)

    async def send_audio(self):
        while True:
            chunk = await self.audio_out_queue.get()
            await self.session.send({"data": chunk, "mime_type": "audio/pcm"})

    async def receive_audio(self):
        while True:
            async for response in self.session.receive():
                server_content = response.server_content
                if server_content is not None:
                    model_turn = server_content.model_turn
                    if model_turn is not None:
                        parts = model_turn.parts

                        for part in parts:
                            if part.text is not None:
                                print(part.text, end="")
                            elif part.inline_data is not None:
                                self.audio_in_queue.put_nowait(part.inline_data.data)

                    server_content.model_turn = None
                    turn_complete = server_content.turn_complete
                    if turn_complete:
                        # If you interrupt the model, it sends a turn_complete.
                        # For interruptions to work, we need to stop playback.
                        # So empty out the audio queue because it may have loaded
                        # much more audio than has played yet.
                        print("Turn complete")
                        while not self.audio_in_queue.empty():
                            self.audio_in_queue.get_nowait()

    async def play_audio(self):
        pya = pyaudio.PyAudio()
        stream = await asyncio.to_thread(
            pya.open,
            format=FORMAT,
            channels=CHANNELS,
            rate=RECEIVE_SAMPLE_RATE,
            output=True,
        )
        while True:
            bytestream = await self.audio_in_queue.get()
            await asyncio.to_thread(stream.write, bytestream)

    async def run(self):
        async with (
            client.aio.live.connect(
                model=MODEL,
                config=CONFIG,
            ) as session,
            asyncio.TaskGroup() as tg,
        ):
            self.session = session

            send_text_task = tg.create_task(self.send_text())

            def cleanup(task):
                for t in tg._tasks:
                    t.cancel()

            send_text_task.add_done_callback(cleanup)

            tg.create_task(self.record_audio())
            tg.create_task(self.send_audio())
            tg.create_task(self.receive_audio())
            tg.create_task(self.play_audio())

            def check_error(task):
                if task.cancelled():
                    return

                if task.exception() is None:
                    return

                e = task.exception()
                traceback.print_exception(None, e, e.__traceback__)
                sys.exit(1)

            for task in tg._tasks:
                task.add_done_callback(check_error)


if __name__ == "__main__":
    main = AudioLoop()
    asyncio.run(main.run())
