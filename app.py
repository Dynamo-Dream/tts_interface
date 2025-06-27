import streamlit as st
import os
import base64
import json
from google.cloud import texttospeech
import google.auth
# --- Configuration and Setup ---

st.set_page_config(
    page_title="Text-to-Speech Converter",
    page_icon="️️🎙️",
    layout="centered",
)

st.title("️🎙️ Google Text-to-Speech App")
st.markdown(
    "Convert your text into natural-sounding speech and download it as an MP3 file."
)

# --- Credential Handling ---
# This block handles the Google Cloud credentials securely.
# It expects 'GOOGLE_API_KEY' and 'GOOGLE_CREDENTIALS' (base64) as environment variables.

try:
    # Get credentials from environment variables
    google_creds_base64 = os.environ.get("GOOGLE_CREDENTIALS")
    google_api_key = os.environ.get("GOOGLE_API_KEY")

    def base64ToString(b):
        return base64.b64decode(b).decode("utf-8")

    credentials, project_id = google.auth.load_credentials_from_dict(
        json.loads(base64ToString(os.getenv("GOOGLE_CREDENTIALS")))
    )

    # The client library will automatically use the credentials dictionary
    client = texttospeech.TextToSpeechClient(credentials=credentials)
    st.sidebar.success("Successfully connected to Google Cloud TTS.")

except Exception as e:
    st.error(f"Error setting up Google Cloud credentials: {e}")
    st.info(
        "Please ensure your 'GOOGLE_API_KEY' and 'GOOGLE_CREDENTIALS' environment variables are correctly set."
    )
    st.stop()


# --- Functions ---


@st.cache_data(show_spinner="Fetching available voices...")
def get_voices():
    """Fetches and caches the list of available voices from Google TTS."""
    try:
        voices_response = client.list_voices()
        voice_list = voices_response.voices

        # We'll create a more user-friendly list for the selectbox
        formatted_voices = {}
        for voice in voice_list:
            name = voice.name
            language = voice.language_codes[0]
            gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name.capitalize()

            # Group by language
            if language not in formatted_voices:
                formatted_voices[language] = []

            # Format: en-US-Wavenet-F (Female)
            display_name = f"{name} ({gender})"
            formatted_voices[language].append((name, display_name))
        return formatted_voices
    except Exception as e:
        st.error(f"Could not fetch voices from Google API: {e}")
        return {}


def synthesize_speech(text, voice_name, speaking_rate, pitch):
    """Calls the Google TTS API to synthesize speech."""
    try:
        synthesis_input = texttospeech.SynthesisInput(text=text)

        voice_params = texttospeech.VoiceSelectionParams(
            name=voice_name,
            language_code="-".join(voice_name.split("-")[:2]),  # e.g., "en-US"
        )

        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.MP3,
            speaking_rate=speaking_rate,
            pitch=pitch,
        )

        response = client.synthesize_speech(
            input=synthesis_input, voice=voice_params, audio_config=audio_config
        )
        return response.audio_content
    except Exception as e:
        st.error(f"API call failed: {e}")
        return None


# --- UI Layout ---

# Sidebar for controls
st.sidebar.header("Audio Controls")

available_voices = get_voices()
if available_voices:
    selected_language = st.sidebar.selectbox(
        "Select Language",
        options=sorted(available_voices.keys()),
        index=sorted(available_voices.keys()).index("en-US"),
    )

    voice_options = available_voices[selected_language]
    # Create a dictionary for easy lookup from display name to actual name
    voice_display_map = {display: name for name, display in voice_options}

    selected_display_voice = st.sidebar.selectbox(
        "Select Voice", options=[display for name, display in voice_options]
    )
    selected_voice_name = voice_display_map[selected_display_voice]

    speaking_rate = st.sidebar.slider(
        "Speaking Speed",
        min_value=0.25,
        max_value=4.0,
        value=1.0,
        step=0.25,
        help="Adjusts the speed of the speech. 1.0 is normal speed.",
    )

    pitch = st.sidebar.slider(
        "Pitch",
        min_value=-20.0,
        max_value=20.0,
        value=0.0,
        step=1.0,
        help="Adjusts the pitch of the voice. 0.0 is the default.",
    )

# Main area for text input
st.header("Enter Your Text")
input_text = st.text_area(
    "Type or paste the text you want to convert to speech.",
    "Hello! Welcome to the Text-to-Speech demonstration powered by Google Cloud.",
    height=150,
)

# Generate Button
if st.button("️Generate Audio", type="primary"):
    if not input_text.strip():
        st.warning("Please enter some text to generate audio.")
    elif not available_voices:
        st.error("Cannot generate audio because voice list is unavailable.")
    else:
        with st.spinner("Generating audio... This may take a moment."):
            audio_content = synthesize_speech(
                input_text, selected_voice_name, speaking_rate, pitch
            )

        if audio_content:
            st.success("Audio generated successfully!")

            # Display audio player
            st.audio(audio_content, format="audio/mp3")

            # Provide download button
            st.download_button(
                label="Download MP3",
                data=audio_content,
                file_name="generated_speech.mp3",
                mime="audio/mpeg",
            )
        else:
            st.error(
                "Failed to generate audio. Please check the logs or your API credentials."
            )
