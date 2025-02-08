# yt-autostream

## Overview
`yt-autostream` is a Python script that automates the process of downloading YouTube videos and audio, normalizing them, mixing them with transitions, and live streaming the final output to YouTube or other RTMP receivers.

## Features
- Downloads video and audio from YouTube playlists
- Normalizes video and audio for consistent quality
- Applies fade transitions between video and audio clips
- Automatically loops the generated video mix while streaming
- Streams the final output to YouTube or any RTMP server
- Configurable parameters for fine-tuning performance

## Installation
### Prerequisites
Ensure you have the following dependencies installed:
- Python 3.8+
- `ffmpeg`
- `yt-dlp`
- `ffmpeg-python`

To install the required Python packages:
```bash
pip install -r requirements.txt
```

### FFmpeg
Make sure FFmpeg is installed and available in your system's PATH. You can check this by running:
```bash
ffmpeg -version
```

## Configuration
All files are stored in the `data` directory:
- `data/downloads` - Stores downloaded videos and audio
- `data/tmp` - Temporary processing files
- `data/rendered` - Final processed files

The script uses the following configuration parameters:
```python
VIDEO_SKIP_START = 180  # Start time in seconds (default: 3 minutes)
VIDEO_DURATION = 60  # Duration to capture (default: 1 minute)
AUDIO_SKIP_START = 180  # Start time in seconds (default: 3 minutes)
AUDIO_DURATION = 300  # Duration to capture (default: 5 minutes)
TRANSITION_DURATION = 6  # Fade transition duration in seconds
FONT_PATH = "Font.TTF"  # Path to custom font for overlays
```

## Usage
### Download and process videos/audio to mix
To start downloading a playlist and render te results to a final video
```python
python main.py process --playlist-url "https://www.youtube.com/.."
```

### Stream to YouTube
To start streaming the final output to YouTube:
```python
python main.py stream --stream-key <youtube stream_key>
```

## TODO List
- Optimize `drawtext` filter by rendering PNG with text and overlaying it
- Add support for reloading the stream when a new file is available
- Implement VAAPI hardware acceleration
- Improve performance of video/audio normalization
- Optimize final rendering performance
- Refactor code into functions for better maintainability
- Define deployment options

