import json
import argparse
import datetime
import os
import time
import subprocess
import requests
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor, as_completed
from ratelimit import limits, sleep_and_retry

MAX_REQUESTS_PER_MINUTE = 95
WORKER_COUNT = 10
REQUEST_INTERVAL = 60 / (MAX_REQUESTS_PER_MINUTE / WORKER_COUNT)  

LANGUAGE_NAME_TO_CODE = {
    "afrikaans": "af",
    "arabic": "ar",
    "armenian": "hy",
    "azerbaijani": "az",
    "belarusian": "be",
    "bosnian": "bs",
    "bulgarian": "bg",
    "catalan": "ca",
    "chinese": "zh",
    "croatian": "hr",
    "czech": "cs",
    "danish": "da",
    "dutch": "nl",
    "english": "en",
    "estonian": "et",
    "finnish": "fi",
    "french": "fr",
    "galician": "gl",
    "german": "de",
    "greek": "el",
    "hebrew": "he",
    "hindi": "hi",
    "hungarian": "hu",
    "icelandic": "is",
    "indonesian": "id",
    "italian": "it",
    "japanese": "ja",
    "kannada": "kn",
    "kazakh": "kk",
    "korean": "ko",
    "latvian": "lv",
    "lithuanian": "lt",
    "macedonian": "mk",
    "malay": "ms",
    "marathi": "mr",
    "maori": "mi",
    "nepali": "ne",
    "norwegian": "no",
    "persian": "fa",
    "polish": "pl",
    "portuguese": "pt",
    "romanian": "ro",
    "russian": "ru",
    "serbian": "sr",
    "slovak": "sk",
    "slovenian": "sl",
    "spanish": "es",
    "swahili": "sw",
    "swedish": "sv",
    "tagalog": "tl",
    "tamil": "ta",
    "thai": "th",
    "turkish": "tr",
    "ukrainian": "uk",
    "urdu": "ur",
    "vietnamese": "vi",
    "welsh": "cy"
}

ISO_639_2_TO_1 = {
    'aar': 'aa',  # Afar
    'abk': 'ab',  # Abkhazian
    'afr': 'af',  # Afrikaans
    'aka': 'ak',  # Akan
    'alb': 'sq',  # Albanian (ISO 639-2 has "alb" for historical reasons, modern code is "sqi")
    'amh': 'am',  # Amharic
    'ara': 'ar',  # Arabic
    'arg': 'an',  # Aragonese
    'arm': 'hy',  # Armenian (ISO 639-2 has "arm", modern code is "hye")
    'asm': 'as',  # Assamese
    'ava': 'av',  # Avaric
    'ave': 'ae',  # Avestan
    'aym': 'ay',  # Aymara
    'aze': 'az',  # Azerbaijani
    'bak': 'ba',  # Bashkir
    'bam': 'bm',  # Bambara
    'baq': 'eu',  # Basque (ISO 639-2 has "baq", modern code is "eus")
    'bel': 'be',  # Belarusian
    'ben': 'bn',  # Bengali
    'bih': 'bh',  # Bihari
    'bis': 'bi',  # Bislama
    'bos': 'bs',  # Bosnian
    'bre': 'br',  # Breton
    'bul': 'bg',  # Bulgarian
    'bur': 'my',  # Burmese (ISO 639-2 has "bur", modern code is "mya")
    'cat': 'ca',  # Catalan
    'ces': 'cs',  # Czech
    'cha': 'ch',  # Chamorro
    'che': 'ce',  # Chechen
    'chi': 'zh',  # Chinese
    'chu': 'cu',  # Church Slavic
    'chv': 'cv',  # Chuvash
    'cor': 'kw',  # Cornish
    'cos': 'co',  # Corsican
    'cre': 'cr',  # Cree
    'cym': 'cy',  # Welsh
    'dan': 'da',  # Danish
    'deu': 'de',  # German
    'div': 'dv',  # Divehi, Dhivehi, Maldivian
    'dut': 'nl',  # Dutch (ISO 639-2 has "dut", modern code is "nld")
    'dzo': 'dz',  # Dzongkha
    'ell': 'el',  # Greek, Modern
    'eng': 'en',  # English
    'epo': 'eo',  # Esperanto
    'est': 'et',  # Estonian
    'eus': 'eu',  # Basque
    'ewe': 'ee',  # Ewe
    'fao': 'fo',  # Faroese
    'fas': 'fa',  # Persian
    'fij': 'fj',  # Fijian
    'fin': 'fi',  # Finnish
    'fra': 'fr',  # French
    'fry': 'fy',  # Western Frisian
    'ful': 'ff',  # Fulah
    'geo': 'ka',  # Georgian (ISO 639-2 has "geo", modern code is "kat")
    'ger': 'de',  # German (ISO 639-2 has "ger", modern code is "deu")
    'gla': 'gd',  # Gaelic, Scottish Gaelic
    'gle': 'ga',  # Irish
    'glg': 'gl',  # Galician
    'glv': 'gv',  # Manx
    'gre': 'el',  # Greek (ISO 639-2 has "gre", modern code is "ell")
    'grn': 'gn',  # Guarani
    'guj': 'gu',  # Gujarati
    'hat': 'ht',  # Haitian, Haitian Creole
    'hau': 'ha',  # Hausa
    'heb': 'he',  # Hebrew
    'her': 'hz',  # Herero
    'hin': 'hi',  # Hindi
    'hmo': 'ho',  # Hiri Motu
    'hrv': 'hr',  # Croatian
    'hun': 'hu',  # Hungarian
    'hye': 'hy',  # Armenian
    'ibo': 'ig',  # Igbo
    'ice': 'is',  # Icelandic (ISO 639-2 has "ice", modern code is "isl")
    'ido': 'io',  # Ido
    'iii': 'ii',  # Sichuan Yi
    'iku': 'iu',  # Inuktitut
    'ile': 'ie',  # Interlingue
    'ina': 'ia',  # Interlingua
    'ind': 'id',  # Indonesian
    'ipk': 'ik',  # Inupiaq
    'isl': 'is',  # Icelandic
    'ita': 'it',  # Italian
    'jav': 'jv',  # Javanese
    'jpn': 'ja',  # Japanese
    'kal': 'kl',  # Kalaallisut, Greenlandic
    'kan': 'kn',  # Kannada
    'kas': 'ks',  # Kashmiri
    'kat': 'ka',  # Georgian
    'kaz': 'kk',  # Kazakh
    'khm': 'km',  # Central Khmer
    'kik': 'ki',  # Kikuyu, Gikuyu
    'kin': 'rw',  # Kinyarwanda
    'kir': 'ky',  # Kirghiz, Kyrgyz
    'kom': 'kv',  # Komi
    'kon': 'kg',  # Kongo
    'kor': 'ko',  # Korean
    'kua': 'kj',  # Kuanyama, Kwanyama
    'kur': 'ku',  # Kurdish
    'lao': 'lo',  # Lao
    'lat': 'la',  # Latin
    'lav': 'lv',  # Latvian
    'lim': 'li',  # Limburgan, Limburger, Limburgish
    'lin': 'ln',  # Lingala
    'lit': 'lt',  # Lithuanian
    'ltz': 'lb',  # Luxembourgish, Letzeburgesch
    'lub': 'lu',  # Luba-Katanga
    'lug': 'lg',  # Ganda
    'mac': 'mk',  # Macedonian (ISO 639-2 has "mac", modern code is "mkd")
    'mal': 'ml',  # Malayalam
    'mao': 'mi',  # Maori (ISO 639-2 has "mao", modern code is "mri")
    'mar': 'mr',  # Marathi
    'may': 'ms',  # Malay (ISO 639-2 has "may", modern code is "msa")
    'mlg': 'mg',  # Malagasy
    'mlt': 'mt',  # Maltese
    'mon': 'mn',  # Mongolian
    'mri': 'mi',  # Maori
    'msa': 'ms',  # Malay
    'mya': 'my',  # Burmese
    'nau': 'na',  # Nauru
    'nav': 'nv',  # Navajo, Navaho
    'nbl': 'nr',  # Ndebele, South; South Ndebele
    'nde': 'nd',  # Ndebele, North; North Ndebele
    'ndo': 'ng',  # Ndonga
    'nep': 'ne',  # Nepali
    'nld': 'nl',  # Dutch
    'nno': 'nn',  # Norwegian Nynorsk, Nynorsk
    'nob': 'nb',  # Norwegian Bokmål, Bokmål
    'nor': 'no',  # Norwegian
    'nya': 'ny',  # Chichewa, Chewa, Nyanja
    'oci': 'oc',  # Occitan (post 1500)
    'oji': 'oj',  # Ojibwa
    'ori': 'or',  # Oriya
    'orm': 'om',  # Oromo
    'oss': 'os',  # Ossetian, Ossetic
    'pan': 'pa',  # Panjabi, Punjabi
    'per': 'fa',  # Persian (ISO 639-2 has "per", modern code is "fas")
    'pol': 'pl',  # Polish
    'por': 'pt',  # Portuguese
    'pus': 'ps',  # Pushto, Pashto
    'que': 'qu',  # Quechua
    'roh': 'rm',  # Romansh
    'ron': 'ro',  # Romanian
    'rus': 'ru',  # Russian
    'sag': 'sg',  # Sango
    'san': 'sa',  # Sanskrit
    'sin': 'si',  # Sinhala, Sinhalese
    'slk': 'sk',  # Slovak
    'slv': 'sl',  # Slovenian
    'sme': 'se',  # Northern Sami
    'smo': 'sm',  # Samoan
    'sna': 'sn',  # Shona
    'snd': 'sd',  # Sindhi
    'som': 'so',  # Somali
    'sqi': 'sq',  # Albanian
    'srd': 'sc',  # Sardinian
    'srp': 'sr',  # Serbian
    'ssw': 'ss',  # Swati
    'sun': 'su',  # Sundanese
    'swa': 'sw',  # Swahili
    'swe': 'sv',  # Swedish
    'tam': 'ta',  # Tamil
    'tel': 'te',  # Telugu
    'tgk': 'tg',  # Tajik
    'tgl': 'tl',  # Tagalog
    'tha': 'th',  # Thai
    'tib': 'bo',  # Tibetan
    'tir': 'ti',  # Tigrinya
    'ton': 'to',  # Tonga (Tonga Islands)
    'tsn': 'tn',  # Tswana
    'tso': 'ts',  # Tsonga
    'tuk': 'tk',  # Turkmen
    'tur': 'tr',  # Turkish
    'twi': 'tw',  # Twi
    'uig': 'ug',  # Uighur, Uyghur
    'ukr': 'uk',  # Ukrainian
    'urd': 'ur',  # Urdu
    'uzb': 'uz',  # Uzbek
    'ven': 've',  # Venda
    'vie': 'vi',  # Vietnamese
    'vol': 'vo',  # Volapük
    'wel': 'cy',  # Welsh
    'wol': 'wo',  # Wolof
    'xho': 'xh',  # Xhosa
    'yid': 'yi',  # Yiddish
    'yor': 'yo',  # Yoruba
    'zha': 'za',  # Zhuang, Chuang
    'zul': 'zu',  # Zulu
}

def extract_audio_from_video(video_file):
    output_audios = []
    # Extract all audio streams
    probe = subprocess.run(["ffprobe", "-loglevel", "error", "-show_entries", "stream=index:stream_tags=language", "-select_streams", "a", "-of", "json", video_file], capture_output=True, text=True, check=True)
    streams = json.loads(probe.stdout)['streams']

    for stream in streams:
        track_index = stream['index']
        language_tag = stream.get('tags', {}).get('language', 'unknown')
        language_code = get_language_code(language_tag)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        output_audio = f"temp_audio_{language_code}_{timestamp}.wav"
        print(f"Extracting audio track {track_index} ({language_code}) to {output_audio}")
        
        # Extract specific audio track
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", video_file, "-map", f"0:{track_index}", "-vn", "-acodec", "pcm_s16le", "-ar", "44100", output_audio],
            check=True)
        output_audios.append((output_audio, language_code))

    return output_audios

def get_language_code(language_code):
    if len(language_code) == 2:
        return language_code
    elif len(language_code) == 3:
        return ISO_639_2_TO_1.get(language_code, 'en')
    else:
        return language_code

def get_iso_639_1_code(language_name):
    return LANGUAGE_NAME_TO_CODE.get(language_name.lower(), 'en')


def transcribe_audio_openai(input_file, chunk_length_ms, start_time_ms, api_key, language="unknown"):
    audio = AudioSegment.from_wav(input_file)
    subtitle_text = 'WEBVTT\n\n'
    detected_language = None

    def transcribe_chunk(start, end, offset):
        audio_chunk = audio[start:end]
        temp_audio_path = f'temp_audio_chunk_{start}_{language}.wav'
        audio_chunk.export(temp_audio_path, format="wav")

        print(f"Transcribing chunk: {start} ms to {end} ms with offset {offset / 1000:.3f} s")
        transcription, chunk_language = openai_transcribe(temp_audio_path, api_key)

        os.remove(temp_audio_path)
        return start, end, transcription, offset, chunk_language

    results = []
    with ThreadPoolExecutor(max_workers=WORKER_COUNT) as executor:
        futures = {executor.submit(transcribe_chunk, start, min(start + chunk_length_ms, len(audio)), start): start
                   for start in range(start_time_ms, len(audio), chunk_length_ms)}

        for future in as_completed(futures):
            start, end, transcription, offset, chunk_language = future.result()
            print(f"Chunk {start} ms to {end} ms transcribed")
            results.append((start, end, transcription, offset))
            if language == 'unknown' and chunk_language:
                detected_language = get_iso_639_1_code(chunk_language)
            time.sleep(REQUEST_INTERVAL)

    results.sort(key=lambda x: x[0])

    for start, end, transcription, offset in results:
        if transcription:
            for segment in transcription['segments']:
                offset_seconds = (offset / 1000)
                seg_start = segment['start'] + offset_seconds
                seg_end = segment['end'] + offset_seconds
                text = segment['text']
                
                formatted_start = format_time(seg_start)
                formatted_end = format_time(seg_end)
                
                subtitle_text += f"{formatted_start} --> {formatted_end}\n{text.strip()}\n\n"

    
    return subtitle_text, detected_language

@sleep_and_retry
@limits(calls=MAX_REQUESTS_PER_MINUTE, period=60)
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
            data = response.json()
            return data, data.get('language')
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return None, None

def format_time(seconds):
    td = datetime.timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    milliseconds = int((td.total_seconds() - total_seconds) * 1000)
    
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Transcribe audio and create subtitle file with correct timestamps')
    parser.add_argument('-i', '--input', help='Input video file path', required=True)
    parser.add_argument('-o', '--output', help='Output subtitle file path', required=False)
    parser.add_argument('-c', '--chunk', type=int, default=10000, help='Chunk length in milliseconds (default: 10000)')
    parser.add_argument('-s', '--start', type=int, default=0, help='Start time in milliseconds (default: 0)')
    parser.add_argument('-k', '--key', help='Your API key')
    parser.add_argument('--auto-name', action='store_true', help='Auto-generate output file name based on detected language')

    args = parser.parse_args()

    start_time = time.time()

    audio_files = extract_audio_from_video(args.input)

    for audio_file, language_code in audio_files:
        print(f"Transcribing track {language_code}")
        subtitle_text, detected_language = transcribe_audio_openai(audio_file, args.chunk, args.start, args.key, language=language_code)
        
        output_file = audio_file
        if args.auto_name:
            output_file = f"{detected_language or language_code}.vtt"
        elif not output_file:
            output_file = f"{os.path.splitext(args.input)[0]}_{detected_language or language_code}.vtt"

        print(f"Saving transcription to {output_file}")
        try:
            with open(output_file, 'w', encoding='utf-8') as subtitle_file:
                subtitle_file.write(subtitle_text)
                print(f"Subtitle file successfully written to {output_file}")
        except IOError as e:
            print(f"Error writing to file {output_file}: {e}")

        os.remove(audio_file)

    end_time = time.time()
    print(f"Transcription completed in {end_time - start_time:.2f} seconds.")


