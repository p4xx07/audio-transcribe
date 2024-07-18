import argparse
import os
import time
import subprocess
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor, as_completed

def extract_audio_from_video(video_file):
    output_audio = "temp_audio.wav"
    subprocess.run(
        ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_file, "-vn", "-acodec", "pcm_s16le", "-ar",
         "44100", output_audio],
        check=True)
    return output_audio

def transcribe_audio_google(input_file, output_file, chunk_length_ms, start_time_ms):
    if input_file.endswith('.mp4') or input_file.endswith('.mkv') or input_file.endswith('.avi'):
        input_file = extract_audio_from_video(input_file)

    recognizer = sr.Recognizer()

    audio = AudioSegment.from_wav(input_file)

    subtitle_text = 'WEBVTT\n\n'
    current_time = start_time_ms
    while current_time < len(audio):
        print("Processing chunk starting at: " + str(current_time) + " ms")

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

def transcribe_audio_openai(input_file, output_file, chunk_length_ms, start_time_ms, api_key):
    if input_file.endswith('.mp4') or input_file.endswith('.mkv') or input_file.endswith('.avi'):
        input_file = extract_audio_from_video(input_file)

    audio = AudioSegment.from_wav(input_file)

    subtitle_text = 'WEBVTT\n\n'

    def transcribe_chunk(start, end, offset):
        audio_chunk = audio[start:end]
        temp_audio_path = f'temp_audio_chunk_{start}.wav'
        audio_chunk.export(temp_audio_path, format="wav")

        print(f"Transcribing chunk: {start} ms to {end} ms with offset {offset / 1000:.3f} s")
        transcription = openai_transcribe(temp_audio_path, api_key)

        os.remove(temp_audio_path)

        return start, end, transcription, offset

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(transcribe_chunk, start, min(start + chunk_length_ms, len(audio)), start): start
                   for start in range(start_time_ms, len(audio), chunk_length_ms)}

        for future in as_completed(futures):
            start, end, transcription, offset = future.result()
            print(f"Chunk {start} ms to {end} ms transcribed")
            results.append((start, end, transcription, offset))

    # Sort results by the start time
    results.sort(key=lambda x: x[0])

    for start, end, transcription, offset in results:
        if transcription:
            for segment in transcription['segments']:
                offset_seconds = (offset / 1000)
                seg_start = segment['start'] +  offset_seconds
                seg_end = segment['end'] + offset_seconds
                text = segment['text']
                subtitle_text += f"{seg_start:.3f} --> {seg_end:.3f}\n{text.strip()}\n\n"

    with open(output_file, 'w') as subtitle_file:
        subtitle_file.write(subtitle_text)

def openai_transcribe(audio_path, api_key):
    with open(audio_path, 'rb') as audio_file:
        response = requests.post(
            'https://api.openai.com/v1/audio/transcriptions',
            headers={
                'Authorization': f'Bearer {api_key}'
            },
            files={
                'file': audio_file
            },
            data={
                'model': 'whisper-1',
                'response_format': 'verbose_json',
                'timestamp_granularities:': ['word']
            }
        )
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transcribe audio and create subtitle file with correct timestamps')
    parser.add_argument('-i', '--input', help='Input audio file path', required=True)
    parser.add_argument('-o', '--output', help='Output subtitle file path', required=True)
    parser.add_argument('-c', '--chunk', type=int, default=10000, help='Chunk length in milliseconds (default: 10000)')
    parser.add_argument('-s', '--start', type=int, default=0, help='Start time in milliseconds (default: 0)')
    parser.add_argument('-k', '--key', help='Your API key')
    parser.add_argument('-p', '--program', help='google or openai', required=True)

    args = parser.parse_args()

    start_time = time.time()
    if args.program == 'google':
        transcribe_audio_google(args.input, args.output, args.chunk, args.start)
    elif args.program == 'openai':
        transcribe_audio_openai(args.input, args.output, args.chunk, args.start, args.key)
    else:
        print(f"Please choose a valid program: google/openai")

    end_time = time.time()

    duration = end_time - start_time
    print(f"Transcription completed in {duration:.2f} seconds.")
