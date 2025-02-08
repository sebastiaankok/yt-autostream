import os

import ffmpeg
import yt_dlp as youtube_dl
from datetime import datetime

# TODO: Optimise drawtext filter for better performance. Render PNG with text and overlay it on video.
# TODO: Add support for reloading stream when a new file is available
# TODO: Add support for VAAPI hardware acceleration
# TODO: Optimise audio normalization performance
# TODO: Optimize video normalization performance
# TODO: Optimize final rendering performance
# TODO: Refactor code into functions for better readability
# TODO: Define deployment options

# Configuration
DATA_DIR = "data"
DL_DIR = DATA_DIR + "/downloads"
TMP_DIR = DATA_DIR + "/tmp"
RENDERED_DIR = DATA_DIR + "/rendered"

# Ensure output directories exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DL_DIR, exist_ok=True)
os.makedirs(TMP_DIR, exist_ok=True)
os.makedirs(RENDERED_DIR, exist_ok=True)

# Video configuration
VIDEO_SKIP_START = 180  # 3 minutes
VIDEO_DURATION = 60  # 2 minutes

# Audio configuration
AUDIO_SKIP_START = 180  # 3 minutes
AUDIO_DURATION = 300  # 5 minutes

TRANSITION_DURATION = 6  # Duration of the fade transition in seconds

FONT_PATH = "Font.TTF"


def get_base_options():
    """Return common options for both video and audio downloads"""
    return {
        "restrictfilenames": True,  # Restrict filenames to only ASCII characters
        "ignoreerrors": True,  # Ignore errors and continue
        "nooverwrites": True,  # Do not overwrite files
        "split_chapters": False,  # Don't split by chapters
        "writethumbnail": False,  # Do not download thumbnails
        "writesubtitles": False,  # Do not download subtitles
        "writeautomaticsub": False,  # Do not download automatic subtitles
        "cookiesfile": "cookies.sqlite",  # File to read cookies from
        "force_keyframes_at_cuts": True,  # Ensure clean cuts at the specified times
    }


def normalize_video(input_path, target_width=1920, target_height=1080):
    """Normalize video using ffmpeg-python"""
    output_path = input_path.replace("_video.", "_video_normalized.")

    if os.path.exists(output_path):
        print(f"Skipping normalization: {input_path}")
        return

    print(f"Normalizing video: {input_path}")
    try:
        # Setup the ffmpeg stream with desired parameters
        stream = (
            ffmpeg.input(input_path)
            .filter("fps", fps=25)
            # Scale video to target resolution while maintaining aspect ratio
            .filter(
                "scale",
                width=f"{target_width}",
                height=f"{target_height}",
                force_original_aspect_ratio="decrease",
            )
            # Pad the video if needed to reach exact target dimensions
            .filter(
                "pad",
                width=f"{target_width}",
                height=f"{target_height}",
                x="(ow-iw)/2",
                y="(oh-ih)/2",
            )
            .output(
                output_path,
                vcodec="libx264",
                crf=23,
                preset="superfast",
                acodec="copy",
                **{"loglevel": "error"},
            )
            .overwrite_output()
        )

        # Run the ffmpeg command
        stream.run(capture_stdout=True, capture_stderr=True)
        print(f"Successfully normalized: {input_path}")

    except ffmpeg.Error as e:
        print(f"Error normalizing {input_path}: {e.stderr.decode()}")
        if os.path.exists(output_path):
            os.remove(output_path)


def download_videos(playlist_url):
    """Download videos from playlist"""
    video_opts = get_base_options()
    video_opts.update(
        {
            "format": "bestvideo[height<=1080][vcodec^=avc1]",  # Best video only
            "outtmpl": {
                "default": os.path.join(DL_DIR, "%(title)s_video.%(ext)s"),
            },
            "download_ranges": lambda info_dict, ydl: [
                {
                    "start_time": VIDEO_SKIP_START,
                    "end_time": VIDEO_SKIP_START + VIDEO_DURATION,
                }
            ],
        }
    )

    with youtube_dl.YoutubeDL(video_opts) as ydl:
        ydl.download([playlist_url])
        ## If video downloaded, normalize it

    # Process all downloaded videos
    for filename in os.listdir(DL_DIR):
        if filename.endswith("_video.mp4") and not filename.endswith(
            "_normalized_video.mp4"
        ):
            input_path = os.path.join(DL_DIR, filename)
            normalize_video(input_path)


def download_audio(playlist_url):
    """Download audio from playlist"""
    audio_opts = get_base_options()
    audio_opts.update(
        {
            "format": "bestaudio[ext=m4a]",  # Best audio only
            "extract_audio": True,
            "outtmpl": {
                "default": os.path.join(DL_DIR, "%(title)s_audio.%(ext)s"),
            },
            "download_ranges": lambda info_dict, ydl: [
                {
                    "start_time": AUDIO_SKIP_START,
                    "end_time": AUDIO_SKIP_START + AUDIO_DURATION,
                }
            ],
        }
    )

    with youtube_dl.YoutubeDL(audio_opts) as ydl:
        ydl.download([playlist_url])


def create_video_mix(output_filename="output_video.mp4"):
    """Create a mix of all normalized videos with fade transitions."""
    # Get all normalized videos
    videos = []
    for filename in sorted(os.listdir(DL_DIR)):
        if filename.endswith("_normalized.mp4"):
            video_path = os.path.join(DL_DIR, filename)
            videos.append(video_path)
            # Print debug info about the video
            probe = ffmpeg.probe(video_path)
            duration = float(probe["streams"][0]["duration"])
            print(f"Video: {filename}, Duration: {duration:.2f} seconds")

    if not videos:
        print("No videos found to mix!")
        return

    print(f"Total videos to mix: {len(videos)}")

    # Create ffmpeg input streams
    inputs = [ffmpeg.input(video) for video in videos]

    # Build the filter complex
    filter_chains = []

    # Initialize with first video
    last_output = inputs[0].video
    current_duration = VIDEO_DURATION

    for i in range(1, len(videos)):
        # Calculate the offset for the transition
        # Each video starts (VIDEO_DURATION - TRANSITION_DURATION) seconds after the previous one
        offset = current_duration - TRANSITION_DURATION
        current_duration += VIDEO_DURATION - TRANSITION_DURATION

        print(f"Adding video {i} at offset: {offset:.2f}s")

        # Apply the xfade filter
        current_video = inputs[i].video
        last_output = ffmpeg.filter(
            [last_output, current_video],
            "xfade",
            transition="fade",
            duration=TRANSITION_DURATION,
            offset=offset,
        )
        filter_chains.append(last_output)

    # Output path
    output_path = os.path.join(TMP_DIR, output_filename)

    try:
        # Build the ffmpeg command
        stream = ffmpeg.output(
            last_output,  # Final video stream after all transitions
            output_path,
            vcodec="libx264",
            crf=23,
            preset="superfast",
            an=None,  # Explicitly disable audio
        ).overwrite_output()

        # Print the generated command for debugging
        print("Generated ffmpeg command:")
        print(stream.compile())

        # Run the ffmpeg command
        stream.run(capture_stdout=True, capture_stderr=True)
        print(f"Successfully created video mix: {output_path}")

        print(f"Moving {output_path} to {RENDERED_DIR}")
        os.rename(output_path, os.path.join(RENDERED_DIR, output_filename))

    except ffmpeg.Error as e:
        print(f"Error creating video mix: {e.stderr.decode()}")
        if os.path.exists(output_path):
            os.remove(output_path)


def get_track_timings():
    """Get track names and their start times from the audio files."""
    track_info = []
    current_time = 0

    for filename in sorted(os.listdir(DL_DIR)):
        if filename.endswith("_audio.m4a"):
            # Extract track name by removing '_audio.m4a' and replacing underscores with spaces
            track_name = filename.replace("_audio.m4a", "").replace("_", " ")
            track_info.append(
                {
                    "name": track_name,
                    "start_time": current_time,
                    "duration": AUDIO_DURATION,
                }
            )
            current_time += (
                AUDIO_DURATION - TRANSITION_DURATION
            )  # Account for crossfade

    return track_info


def create_audio_mix(output_filename="output_audio.mp4"):
    """Create a mix of all audio with fade transitions."""
    # Get all audio files
    audio_files = []
    for filename in sorted(os.listdir(DL_DIR)):
        if filename.endswith("_audio.m4a"):
            audio_path = os.path.join(DL_DIR, filename)
            audio_files.append(audio_path)
            # Print debug info about the audio
            probe = ffmpeg.probe(audio_path)
            duration = float(probe["streams"][0]["duration"])
            print(f"Audio: {filename}, Duration: {duration:.2f} seconds")

    if not audio_files:
        print("No audio files found to mix!")
        return

    print(f"Total audio files to mix: {len(audio_files)}")

    # Create ffmpeg input streams with normalization
    normalized_inputs = []
    for audio in audio_files:
        # First pass to analyze audio
        input_stream = ffmpeg.input(audio)

        # Add normalized audio to our inputs
        normalized = input_stream.audio.filter(
            "loudnorm",
            I="-27",  # Integrated loudness target (even quieter)
            LRA="11",  # Loudness range
            TP="-3.0",  # True peak (lowered further to prevent clipping)
        )
        normalized_inputs.append(normalized)

    # Build the filter complex
    filter_chains = []

    # Initialize with first normalized audio
    last_output = normalized_inputs[0]
    current_duration = AUDIO_DURATION

    for i in range(1, len(audio_files)):
        # Calculate the offset for the transition
        offset = current_duration - TRANSITION_DURATION
        current_duration += AUDIO_DURATION - TRANSITION_DURATION

        print(f"Adding audio {i} at offset: {offset:.2f}s")

        # Apply the acrossfade filter with normalized audio
        current_audio = normalized_inputs[i]
        last_output = ffmpeg.filter(
            [last_output, current_audio],
            "acrossfade",
            duration=TRANSITION_DURATION,
            curve1="tri",
            curve2="tri",
            d=TRANSITION_DURATION,
        )
        filter_chains.append(last_output)

    # Output path
    output_path = os.path.join(TMP_DIR, output_filename)

    try:
        # Build the ffmpeg command
        stream = ffmpeg.output(
            last_output,  # Final audio stream after all transitions
            output_path,
            acodec="aac",
            **{"b:a": "192k"},
            vn=None,  # Explicitly disable video
        ).overwrite_output()

        # Print the generated command for debugging
        print("Generated ffmpeg command:")
        print(stream.compile())

        # Run the ffmpeg command
        stream.run(capture_stdout=True, capture_stderr=True)
        print(f"Successfully created audio mix: {output_path}")

        print(f"Moving {output_path} to {RENDERED_DIR}")
        os.rename(output_path, os.path.join(RENDERED_DIR, output_filename))

    except ffmpeg.Error as e:
        print(f"Error creating audio mix: {e.stderr.decode()}")
        if os.path.exists(output_path):
            os.remove(output_path)


def render_result(
    video_file="output_video.mp4",
    audio_file="output_audio.mp4",
    output_file=None,
):
    """Combine video and audio mix with track name overlays."""

    if output_file is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M")
        output_file = f"final_output_{timestamp}.mp4"

    video_path = os.path.join(RENDERED_DIR, video_file)
    audio_path = os.path.join(RENDERED_DIR, audio_file)
    output_path = os.path.join(TMP_DIR, output_file)

    # Get track timing information
    track_info = get_track_timings()

    # Get audio and video durations
    audio_probe = ffmpeg.probe(audio_path)
    video_probe = ffmpeg.probe(video_path)
    audio_duration = float(audio_probe["streams"][0]["duration"])
    video_duration = float(video_probe["streams"][0]["duration"])

    # Calculate how many times to loop the video
    loop_times = int(audio_duration / video_duration) + 1

    # Create video input with explicit loop count and trim to audio duration
    video = (
        ffmpeg.input(video_path, stream_loop=loop_times)
        .filter("setpts", "PTS-STARTPTS")
        .filter("trim", duration=audio_duration)
    )
    audio = ffmpeg.input(audio_path)

    # Create drawtext filters for each track
    video_with_text = video

    for track in track_info:
        # Create fade-in and fade-out times
        fade_duration = min(TRANSITION_DURATION, 2)  # Use shorter fade for text
        start_time = track["start_time"]
        end_time = start_time + track["duration"] - TRANSITION_DURATION

        # Split track name into title and rest (if there's a hyphen)
        parts = track["name"].split(" - ", 1)
        title = parts[0] if parts else track["name"]
        # subtitle = parts[1] if len(parts) > 1 else ''

        # Title parameters (larger, positioned at bottom left)
        if FONT_PATH and os.path.exists(FONT_PATH):
            title_params = {
                "text": title,
                "fontcolor": "white",
                "fontfile": FONT_PATH,
                "fontsize": "36",
                "x": "20",  # 20 pixels from left edge
                "y": "h-th-20",  # 20 pixels from bottom
                "enable": f"between(t,{start_time},{end_time})",
                "alpha": f"if(lt(t,{start_time + fade_duration}),((t-{start_time})/{fade_duration}),"
                f"if(gt(t,{end_time - fade_duration}),(({end_time}-t)/{fade_duration}),1))",
            }
        else:
            title_params = {
                "text": title,
                "fontcolor": "white",
                "fontsize": "36",
                "x": "20",  # 20 pixels from left edge
                "y": "h-th-20",  # 20 pixels from bottom
                "enable": f"between(t,{start_time},{end_time})",
                "alpha": f"if(lt(t,{start_time + fade_duration}),((t-{start_time})/{fade_duration}),"
                f"if(gt(t,{end_time - fade_duration}),(({end_time}-t)/{fade_duration}),1))",
            }

        # Apply the drawtext filters
        video_with_text = ffmpeg.filter(video_with_text, "drawtext", **title_params)
    try:
        # Add fade in/out effects to the video
        fade_duration = 5  # 2 second fade duration

        # Apply fade in/out effects
        video_with_effects = ffmpeg.filter(
            video_with_text, "fade", type="in", duration=fade_duration
        )
        video_with_effects = ffmpeg.filter(
            video_with_effects,
            "fade",
            type="out",
            duration=fade_duration,
            start_time=audio_duration - fade_duration,
        )

        # Combine video and audio
        stream = ffmpeg.output(
            video_with_effects,
            audio.audio,
            output_path,
            vcodec="libx264",
            acodec="aac",
            **{"b:a": "192k"},
            preset="superfast",
            crf=23,
        ).overwrite_output()

        # Print the generated command for debugging
        print("Generated ffmpeg command:")
        print(stream.compile())

        # Run the ffmpeg command
        stream.run(capture_stdout=True, capture_stderr=True)
        print(f"Successfully created final output: {output_path}")

        print(f"Moving {output_path} to {RENDERED_DIR}")
        os.rename(output_path, os.path.join(RENDERED_DIR, output_file))

    except ffmpeg.Error as e:
        print(f"Error creating final output: {e.stderr.decode()}")
        if os.path.exists(output_path):
            os.remove(output_path)


# Create the mixes
def stream_to_youtube(input_file=None, rtmp_url=None, stream_key=None):
    """
    Stream the input file to YouTube RTMP server in an infinite loop
    Args:
        input_file (str): The file to stream
        rtmp_url (str): YouTube RTMP URL (default: rtmp://a.rtmp.youtube.com/live2)
        stream_key (str): Your YouTube stream key
    """
    if not rtmp_url:
        rtmp_url = "rtmp://a.rtmp.youtube.com/live2"

    if not stream_key:
        raise ValueError("YouTube stream key is required")

    # Find the latest rendered file if input_file is not provided
    if input_file is None:
        files = [f for f in os.listdir(RENDERED_DIR) if f.startswith("final_output")]
        if not files:
            raise FileNotFoundError("No rendered files found")
        input_file = sorted(files)[-1]

    input_path = os.path.join(RENDERED_DIR, input_file)
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    # Full RTMP URL with stream key
    full_rtmp_url = f"{rtmp_url}/{stream_key}"

    try:
        # Setup the stream with loop input and consistent output settings
        stream = (
            ffmpeg.input(
                input_path, stream_loop=-1, re=None
            )  # -1 means infinite loop, re=None adds 'real-time' flag
            # .filter("format", "nv12")  # VA-API requires NV12 (equivalent to yuv420p)
            # .filter("hwupload")  # Upload to GPU
            .output(
                full_rtmp_url,
                format="flv",
                # vcodec="h264_vaapi",
                # vaapi_device="/dev/dri/renderD128",
                # vcodec="h264_qsv",
                vcodec="libx264",
                acodec="aac",
                **{
                    "b:v": "4500k",  # Video bitrate
                    "b:a": "192k",  # Audio bitrate
                    "bufsize": "8192k",
                    "maxrate": "4500k",
                    "preset": "veryfast",
                    "g": "50",  # Keyframe interval
                    "r": "25",  # Output framerate
                    # "profile:v": "main",  # Ensures yuv420p compatibility
                    # "qp": "20",  # Quality parameter (lower = better quality)
                },
            )
            .overwrite_output()
        )

        print("Starting stream to YouTube...")
        print("Press Ctrl+C to stop the stream")

        # Run the ffmpeg command
        stream.run(capture_stdout=True, capture_stderr=True)

    except ffmpeg.Error as e:
        print(f"Streaming error: {e.stderr.decode()}")
    except KeyboardInterrupt:
        print("\nStream stopped by user")


def main():
    """Main entry point with argument parsing"""
    import argparse

    parser = argparse.ArgumentParser(
        description="YouTube Playlist Processor and Streamer"
    )
    parser.add_argument(
        "action",
        choices=["process", "stream"],
        help='Action to perform: "process" to download and process files, '
        '"stream" to start streaming',
    )
    parser.add_argument(
        "--playlist-url",
        help="YouTube playlist URL (required for process action)",
    )
    parser.add_argument(
        "--stream-key",
        help="YouTube stream key (required for stream action)",
    )
    parser.add_argument(
        "--skip-dl",
        help="YouTube stream key (required for stream action)",
    )
    parser.add_argument(
        "--skip-video-mixing",
        help="YouTube stream key (required for stream action)",
    )
    parser.add_argument(
        "--skip-audio-mixing",
        help="YouTube stream key (required for stream action)",
    )

    args = parser.parse_args()

    # Validate required arguments based on action
    if args.action == "process" and not args.playlist_url:
        parser.error("--playlist-url is required when action is 'process'")
    elif args.action == "stream" and not args.stream_key:
        parser.error("--stream-key is required when action is 'stream'")

    if args.action == "process":
        """Download and process all files"""
        if not args.skip_dl:
            download_videos(args.playlist_url)
            download_audio(args.playlist_url)
        if not args.skip_video_mixing:
            create_video_mix()

        if not args.skip_audio_mixing:
            create_audio_mix()

        render_result()
    elif args.action == "stream":
        stream_to_youtube(stream_key=args.stream_key)


if __name__ == "__main__":
    main()
