
import requests
import whisper
import os
import openai

def download_and_transcribe(url: str, model_name: str = "base") -> str:
    """
    Downloads an audio file from the given URL, then uses Whisper
    to transcribe the file. Finally, deletes the temporary file.

    :param url: The URL of the audio file to download.
    :param model_name: The name of the Whisper model to load (e.g., "tiny", "base", "small", "medium", "large").
    :return: The transcription text as a string.
    """
    
    response = requests.get(url)
    response.raise_for_status()
    
    temp_filename = "temp_audio_file"
    with open(temp_filename, "wb") as f:
        f.write(response.content)
    
    model = whisper.load_model(model_name)
    
    result = model.transcribe(temp_filename)
    
    os.remove(temp_filename)
    
    return result["text"]

def generate_personal_diary(transcription: str, openai_api_key: str, model: str = "gpt-3.5-turbo") -> str:
    """
    Converts a transcription string into a structured personal diary journaling note using OpenAI's LLM.

    :param transcription: The transcription text to be structured.
    :param openai_api_key: Your OpenAI API key.
    :param model: The OpenAI model to use (default: "gpt-3.5-turbo").
    :return: A structured personal diary journaling note.
    """
    # Set your OpenAI API key
    openai.api_key = openai_api_key

    # Create a simple but effective prompt for structuring the transcription into a personal diary entry.
    prompt = (
        "Convert the following transcription into a structured personal diary journaling note. "
        "Include clear sections such as Date, Mood, Key Events, and Reflections. "
        "Ensure the note feels personal and reflective.\\n\\n"
        f"Transcription:\\n{transcription}"
    )

    # Call the OpenAI ChatCompletion endpoint with a simple system and user message.
    response = openai.ChatCompletion.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are an assistant that helps convert plain text into a structured personal diary entry."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
        max_tokens=500,
    )

    # Extract and return the resulting structured note.
    diary_note = response.choices[0].message["content"].strip()
    return diary_note