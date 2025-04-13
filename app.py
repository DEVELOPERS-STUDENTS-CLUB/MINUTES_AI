from flask import Flask, request, jsonify, render_template
import os
import uuid
import subprocess
import google.generativeai as genai
import speech_recognition as sr

# Configure your Gemini API key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def convert_to_wav(input_path):
    output_path = input_path.rsplit('.', 1)[0] + '_converted.wav'
    command = [
        'ffmpeg', '-y', '-i', input_path,
        '-acodec', 'pcm_s16le', '-ac', '1', '-ar', '16000', output_path
    ]
    subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return output_path

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_audio():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    # Save original file
    original_path = os.path.join(UPLOAD_FOLDER, str(uuid.uuid4()) + "_" + file.filename)
    file.save(original_path)

    # Convert to compatible WAV
    converted_path = convert_to_wav(original_path)

    # Convert speech to text
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(converted_path) as source:
            audio = recognizer.record(source)
            transcript = recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        transcript = "Could not understand audio"
    except sr.RequestError as e:
        transcript = f"Error with Google Speech Recognition API: {e}"
    except ValueError:
        transcript = "Unsupported audio format or corrupted file."

    # Summarize with Gemini
    model = genai.GenerativeModel("gemini-pro")
    summary_prompt = f"Summarize the following meeting transcript:\n\n{transcript}"
    response = model.generate_content(summary_prompt)
    summary = response.text

    return jsonify({
        'transcript': transcript,
        'summary': summary
    })

if __name__ == '__main__':
    app.run(debug=True)
