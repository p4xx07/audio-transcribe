# Audio Transcribe

This script transcribes audio and video files into SubRip (.srt) subtitle files with correct timestamps.

## Usage

### Prerequisites

- Python 3.x
- FFmpeg installed

### Installation

1. Install required Python libraries:
   ```bash
   pip install -r requirements.txt
   ```

2. Ensure you have FFmpeg installed. If not, install FFmpeg by following the instructions for your operating system:

   - **Linux:** Use your package manager (e.g., `apt`, `yum`) to install FFmpeg.
   - **macOS:** Install FFmpeg via Homebrew: `brew install ffmpeg`.
   - **Windows:** Download the FFmpeg binaries from [ffmpeg.org](https://ffmpeg.org/download.html) and add the `ffmpeg` executable to your system PATH.

### Running the Script

Run the script using the command line:

```bash
python main.py -i input_file_path -o output_file_path -c chunk_length -s start_time -p program -k api_key
```

Replace the following arguments:
- `input_file_path`: Path to the input audio or video file.
- `output_file_path`: Path for the output subtitle file (.srt).
- `chunk_length`: Chunk length in milliseconds (default: 10000).
- `start_time`: Start time in milliseconds (default: 0).
- `program`: Program to use for transcription, either "google" or "openai".
- `api_key`: API key for the OpenAI transcription service (required if program is "openai").

**Examples:**

Transcribe video file or audio file:
```bash
python script_name.py -i input_video.mp4 -o output_subtitle.srt -c 5000 -s 10000 -p openai -k your_openai_api_key

```

**Note:** Ensure you have proper permissions and necessary codecs installed to handle the input audio/video file formats.
