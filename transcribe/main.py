import argparse
import os

import speech_recognition as sr
import subprocess
from pydub import AudioSegment


def extract_audio_from_video(video_file):
    output_audio = "temp_audio.wav"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_file, "-vn", "-acodec", "pcm_s16le", "-ar", "44100", output_audio],
                   check=True)

    return output_audio


def transcribe_audio(input_file, output_file, chunk_length_ms, start_time_ms):
    if input_file.endswith('.mp4') or input_file.endswith('.mkv') or input_file.endswith('.avi'):
        input_file = extract_audio_from_video(input_file)

    recognizer = sr.Recognizer()

    audio = AudioSegment.from_wav(input_file)

    subtitle_text = ''

    current_time = start_time_ms
    while current_time < len(audio):
        end_time = min(current_time + chunk_length_ms, len(audio))

        audio_chunk = audio[current_time:end_time]

        temp_audio_path = 'temp_audio.wav'
        audio_chunk.export(temp_audio_path, format="wav")

        with sr.AudioFile(temp_audio_path) as source:
            audio_data = recognizer.record(source)

            try:
                text = recognizer.recognize_google(audio_data)
                subtitle_text += f"{current_time // 1000} --> {end_time // 1000}\n{text}\n\n"
            except sr.UnknownValueError:
                subtitle_text += ''
            except sr.RequestError as e:
                subtitle_text += ''
                print(f"Error with the request; {e}")

        current_time = end_time
        os.remove(temp_audio_path)

    with open(output_file, 'w') as subtitle_file:
        subtitle_file.write(subtitle_text)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transcribe audio and create subtitle file with correct timestamps')
    parser.add_argument('-i', '--input', help='Input audio file path', required=True)
    parser.add_argument('-o', '--output', help='Output subtitle file path', required=True)
    parser.add_argument('-c', '--chunk', type=int, default=10000, help='Chunk length in milliseconds (default: 10000)')
    parser.add_argument('-s', '--start', type=int, default=0, help='Start time in milliseconds (default: 0)')

    args = parser.parse_args()

    transcribe_audio(args.input, args.output, args.chunk, args.start)
