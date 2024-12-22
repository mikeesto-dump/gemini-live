# Gemini Live

Exploring Gemini's Multimodal Live API.

- `script.py`: A script to interact with the API.
- `app.py`: A Flask app to interact with the API.

## Installing (TODO)

- Requirements.txt file
- API Key

## Voice activity detection

The model [automatically performs voice activity detection](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live#voice-activity-detection). VAD is always enabled and is not configurable. This provides the opportunity for a natural flowing conversation but in practice is problematic if you are using a speaker and a microphone - the audio feedback stops the model itself. It also seems to be problematic in a noisy ambient environment. Wearing headphones at the moment seems like the only viable approach.

What I have done is change the script so that when the model is speaking, no input audio is sent.

## Session duration

Sessions duration is limited to [15 minutes](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live#maximum-session-duration) for audio. When the session duration exceeds the limit, the connection is terminated. [3 concurrent sessions](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live#rate-limits) per API key are allowed.

## Video input

Video and audio input is [limited to 2 minutes](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live#maximum-session-duration).

## Things to look into

- How to handle keyboard interrupt nicely?
