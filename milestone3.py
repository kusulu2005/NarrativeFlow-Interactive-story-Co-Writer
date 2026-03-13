import streamlit as st
import random
import time
from datetime import datetime
import hashlib
import json
import os
import re
import ollama
import threading
from functools import wraps

# Try to import flask, with helpful error message if not installed
try:
    from flask import Flask, request, jsonify
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    st.error("⚠️ Flask is not installed. Please run: pip install flask")
    st.stop()

# ============================================
# PROJECT CONFIGURATION
# ============================================
PROJECT_NAME = "AetherTales"

st.set_page_config(
    page_title=f"{PROJECT_NAME} - Infinite Imagination",
    page_icon="🔮",
    layout="wide",
)

# Use this for the main title on the landing page
st.markdown(f"<h1 style='text-align: center;'>🔮 {PROJECT_NAME}</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #60a5fa;'>Where Imagination Meets Integrity</p>", unsafe_allow_html=True)

# ============================================
# API CONFIGURATION
# ============================================

API_PORT = 5000
API_HOST = "0.0.0.0"
API_KEY_FILE = "api_keys.json"
api_app = Flask(__name__)
api_thread = None

# API Key management
def init_api_keys():
    """Initialize API keys file"""
    if not os.path.exists(API_KEY_FILE):
        with open(API_KEY_FILE, 'w') as f:
            json.dump({}, f)

def generate_api_key():
    """Generate a new API key"""
    return hashlib.sha256(f"{random.random()}{time.time()}{os.urandom(16)}".encode()).hexdigest()[:32]

def save_api_key(user_email, key_name="Default"):
    """Save API key for user"""
    with open(API_KEY_FILE, 'r') as f:
        keys = json.load(f)
    
    api_key = generate_api_key()
    if user_email not in keys:
        keys[user_email] = []
    
    keys[user_email].append({
        'key': api_key,
        'name': key_name,
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'last_used': None,
        'calls': 0
    })
    
    with open(API_KEY_FILE, 'w') as f:
        json.dump(keys, f, indent=2)
    
    return api_key

def validate_api_key(api_key):
    """Validate if API key exists"""
    with open(API_KEY_FILE, 'r') as f:
        keys = json.load(f)
    
    for user_email, user_keys in keys.items():
        for key_info in user_keys:
            if key_info['key'] == api_key:
                # Update last used and call count
                key_info['last_used'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                key_info['calls'] += 1
                
                with open(API_KEY_FILE, 'w') as f:
                    json.dump(keys, f, indent=2)
                
                return user_email, key_info
    return None, None

def get_user_api_keys(user_email):
    """Get all API keys for a user"""
    with open(API_KEY_FILE, 'r') as f:
        keys = json.load(f)
    return keys.get(user_email, [])

def revoke_api_key(user_email, api_key):
    """Revoke an API key"""
    with open(API_KEY_FILE, 'r') as f:
        keys = json.load(f)
    
    if user_email in keys:
        keys[user_email] = [k for k in keys[user_email] if k['key'] != api_key]
        
        with open(API_KEY_FILE, 'w') as f:
            json.dump(keys, f, indent=2)
        return True
    return False

# Initialize API keys
init_api_keys()

# ============================================
# FLASK API ENDPOINTS
# ============================================

def require_api_key(f):
    """Decorator to require API key"""
    @wraps(f)
    def decorated(*args, **kwargs):
        api_key = request.headers.get('X-API-Key')
        if not api_key:
            return jsonify({'error': 'API key is required'}), 401
        
        user_email, key_info = validate_api_key(api_key)
        if not user_email:
            return jsonify({'error': 'Invalid API key'}), 401
        
        return f(user_email, key_info, *args, **kwargs)
    return decorated

@api_app.route('/api/v1/generate-story', methods=['POST'])
@require_api_key
def api_generate_story(user_email, key_info):
    """Generate a story via API"""
    try:
        data = request.json
        prompt = data.get('prompt', '')
        emotion = data.get('emotion', 'excited')
        genre = data.get('genre', 'fantasy')
        use_ollama = data.get('use_ollama', False)
        
        if not prompt:
            return jsonify({'error': 'Prompt is required'}), 400
        
        # Generate story using combined generator
        story, story_type = generate_combined_story(prompt, emotion, genre, use_ollama)
        
        return jsonify({
            'success': True,
            'story': story,
            'type': story_type,
            'emotion': emotion,
            'genre': genre,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_app.route('/api/v1/health', methods=['GET'])
def api_health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'ollama_connected': check_ollama_connection()
    }), 200

@api_app.route('/api/v1/models', methods=['GET'])
@require_api_key
def api_get_models(user_email, key_info):
    """Get available models"""
    models = {
        'trained_bot': ['StoryBot v1.0 - Emotion-based trained story generator'],
        'ollama': []
    }
    
    if check_ollama_connection():
        models['ollama'] = get_available_models()
    
    return jsonify(models), 200

@api_app.route('/api/v1/emotions', methods=['GET'])
def api_get_emotions():
    """Get available emotions"""
    emotions = ['happy', 'sad', 'angry', 'tired', 'curious', 'scared', 'loved', 'excited']
    return jsonify({'emotions': emotions}), 200

@api_app.route('/api/v1/genres', methods=['GET'])
def api_get_genres():
    """Get available genres"""
    genres = ['fantasy', 'adventure', 'scifi', 'mystery', 'romance', 'horror']
    return jsonify({'genres': genres}), 200

@api_app.route('/api/v1/user/stats', methods=['GET'])
@require_api_key
def api_user_stats(user_email, key_info):
    """Get user API usage stats"""
    return jsonify({
        'user': user_email,
        'api_key': key_info['key'][:8] + '...',
        'key_name': key_info['name'],
        'created_at': key_info['created_at'],
        'last_used': key_info['last_used'],
        'total_calls': key_info['calls']
    }), 200

# ============================================
# FUNCTION TO START API SERVER
# ============================================

def start_api_server():
    """Start the Flask API server in a separate thread"""
    global api_thread
    
    def run_api():
        api_app.run(host=API_HOST, port=API_PORT, debug=False, use_reloader=False, threaded=True)
    
    if api_thread is None or not api_thread.is_alive():
        api_thread = threading.Thread(target=run_api, daemon=True)
        api_thread.start()
        return True
    return False

# Start API server automatically (runs in background)
try:
    if FLASK_AVAILABLE:
        start_api_server()
except Exception as e:
    print(f"API server could not start: {e}")

# ============================================
# USER AUTHENTICATION SYSTEM
# ============================================

USER_DATA_FILE = "users.json"

def init_user_data():
    """Initialize user data file if it doesn't exist"""
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, 'w') as f:
            json.dump({}, f)

def hash_password(password):
    """Hash password for security"""
    return hashlib.sha256(password.encode()).hexdigest()

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def save_user(email, password, user_details=None):
    """Save user with any password (no restrictions)"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    
    users[email] = {
        'password': hash_password(password),
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'stories_count': 0,
        'details_provided': False,
        'user_details': user_details or {}
    }
    
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def verify_user(email, password):
    """Verify user credentials"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    if email in users:
        return users[email]['password'] == hash_password(password)
    return False

def user_exists(email):
    """Check if user exists"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    return email in users

def get_user_data(email):
    """Get user data"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    return users.get(email, {})

# Initialize user data
init_user_data()

# ============================================
# EMOTION-BASED BACKGROUND IMAGES
# ============================================

# Beautiful, emotionally evocative background images
background_images = {
    'default': 'https://images.unsplash.com/photo-1519791883288-dc8bd696e667?auto=format&fit=crop&q=80&w=1600',
    'happy': 'https://images.pexels.com/photos/1763075/pexels-photo-1763075.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'sad': 'https://images.unsplash.com/photo-1490730141103-6cac27aaab94?auto=format&fit=crop&q=80&w=1600',
    'angry': 'https://images.pexels.com/photos/733174/pexels-photo-733174.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'tired': 'https://images.pexels.com/photos/247599/pexels-photo-247599.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'curious': 'https://images.unsplash.com/photo-1502134249126-9f3755a50d78?auto=format&fit=crop&q=80&w=1600',
    'scared': 'https://images.pexels.com/photos/167699/pexels-photo-167699.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'loved': 'https://images.pexels.com/photos/1024960/pexels-photo-1024960.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'excited': 'https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&q=80&w=1600',
}

# Emotion color schemes for UI elements
emotion_colors = {
    'happy': {
        'primary': '#FFD700',
        'secondary': '#FFA500',
        'gradient': 'linear-gradient(135deg, #FFD700, #FFA500, #FF8C00)',
        'accent': '#FF69B4'
    },
    'sad': {
        'primary': '#4A90E2',
        'secondary': '#357ABD',
        'gradient': 'linear-gradient(135deg, #4A90E2, #6A5ACD, #4169E1)',
        'accent': '#9370DB'
    },
    'angry': {
        'primary': '#FF4444',
        'secondary': '#CC0000',
        'gradient': 'linear-gradient(135deg, #FF4444, #FF6B6B, #FF4500)',
        'accent': '#FF8C00'
    },
    'tired': {
        'primary': '#808080',
        'secondary': '#666666',
        'gradient': 'linear-gradient(135deg, #808080, #A9A9A9, #C0C0C0)',
        'accent': '#B8860B'
    },
    'curious': {
        'primary': '#FF6B6B',
        'secondary': '#FF5252',
        'gradient': 'linear-gradient(135deg, #FF6B6B, #FF8C42, #FFD700)',
        'accent': '#4ECDC4'
    },
    'scared': {
        'primary': '#800080',
        'secondary': '#660066',
        'gradient': 'linear-gradient(135deg, #800080, #9932CC, #8A2BE2)',
        'accent': '#9400D3'
    },
    'loved': {
        'primary': '#FF69B4',
        'secondary': '#FF1493',
        'gradient': 'linear-gradient(135deg, #FF69B4, #FFB6C1, #FFC0CB)',
        'accent': '#FF4500'
    },
    'excited': {
        'primary': '#FFA500',
        'secondary': '#FF8C00',
        'gradient': 'linear-gradient(135deg, #FFA500, #FFD700, #FF8C00)',
        'accent': '#00CED1'
    }
}

# Beautiful storytelling image for login page
storytelling_image = 'https://images.unsplash.com/photo-1519791883288-dc8bd696e667?auto=format&fit=crop&q=80&w=1600'

# ============================================
# FUNCTION TO GET EMOTION-BASED BACKGROUND CSS
# ============================================

def get_emotion_background_css(emotion):
    """Get CSS for emotion-based background with color overlay"""
    bg_url = background_images.get(emotion, background_images['default'])
    color_scheme = emotion_colors.get(emotion, emotion_colors['excited'])
    
    return f"""
    <style>
        .stApp {{
            background: url('{bg_url}') !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
            transition: background-image 0.5s ease;
        }}
        
        /* Beautiful gradient overlay based on emotion */
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: {color_scheme['gradient']};
            opacity: 0.25;
            z-index: -1;
            pointer-events: none;
            animation: gradientShift 10s ease infinite;
        }}
        
        @keyframes gradientShift {{
            0% {{ opacity: 0.2; }}
            50% {{ opacity: 0.3; }}
            100% {{ opacity: 0.2; }}
        }}
        
        /* Emotion-based glow effect on containers */
        .story-container, .user-message, .bot-message, .current-emotion, .details-container {{
            border-left: 5px solid {color_scheme['primary']} !important;
            box-shadow: 0 4px 20px {color_scheme['primary']}80 !important;
            transition: all 0.3s ease;
        }}
        
        .story-container:hover, .user-message:hover, .bot-message:hover, .details-container:hover {{
            box-shadow: 0 8px 30px {color_scheme['primary']} !important;
            transform: translateY(-2px);
        }}
        
        /* Emotion-based button hover effect */
        .stButton button:hover {{
            background: {color_scheme['gradient']} !important;
            transform: translateY(-2px);
            box-shadow: 0 6px 20px {color_scheme['primary']} !important;
        }}
        
        /* Emotion-based accent elements */
        .current-emotion {{
            background: linear-gradient(135deg, {color_scheme['primary']}40, {color_scheme['secondary']}40) !important;
            backdrop-filter: blur(10px);
            border: 1px solid {color_scheme['primary']}60 !important;
        }}
    </style>
    """

# ============================================
# COMBINED STORY GENERATOR (OLLAMA + TRAINED BOT)
# ============================================

class StoryBot:
    """A trained story generation bot that creates stories based on user desires"""
    
    def __init__(self):
        # Extensive character name bank
        self.protagonists = [
            'Elena', 'Marcus', 'Sofia', 'James', 'Isabella', 'Oliver', 'Amara', 'Theo', 'Luna', 'Caspian',
            'Aria', 'Dorian', 'Freya', 'Rowan', 'Silas', 'Elara', 'Jasper', 'Iris', 'Corvin', 'Lyra',
            'Magnus', 'Nova', 'Orion', 'Willow', 'Atlas', 'Seraphina', 'Phoenix', 'Raven', 'Sterling', 'Vesper',
            'Aurora', 'Caleb', 'Delilah', 'Ezra', 'Flora', 'Gideon', 'Helena', 'Ignatius', 'Juniper', 'Kai',
            'Zara', 'Kael', 'Mira', 'Finn', 'Ivy', 'Leo', 'Maya', 'Oscar', 'Rosa', 'Felix'
        ]
        
        self.companions = [
            'Samuel', 'Naomi', 'Ezra', 'Cleo', 'Felix', 'Maya', 'Oscar', 'Zara', 'Leo', 'Rosa',
            'Milo', 'Stella', 'Ivy', 'Hugo', 'Mira', 'Kai', 'Lia', 'Axel', 'Nina', 'Quinn',
            'Owen', 'Pearl', 'Remy', 'Sage', 'Tess', 'Vera', 'Wren', 'Xena', 'Yvette', 'Zane'
        ]
        
        self.antagonists = [
            'Malakai', 'Morgana', 'Victor', 'Lilith', 'Damien', 'Ravenna', 'Corbin', 'Seraphine',
            'Draven', 'Morana', 'Kael', 'Morrigan', 'Valtor', 'Zelda', 'Gideon', 'Helena',
            'Ignatius', 'Jezebel', 'Kain', 'Lucian', 'Mortimer', 'Nyx', 'Obsidian', 'Pandora'
        ]
        
        # Rich location database per genre
        self.locations = {
            'fantasy': [
                'the Enchanted Forest where trees whisper ancient secrets',
                'the Floating Castle of Serendell',
                "the Dragon's Lair beneath the Crystal Mountains",
                'the Fairy Kingdom of Luminara',
                "the Wizard's Tower at the Edge of Reality",
                'the Lost City of Eldoria',
                'the Crystal Caves of Avalon',
                'the Temple of the Moon Goddess'
            ],
            'adventure': [
                'the Mysterious Island of Kalypso',
                'the Hidden Valley of the Ancients',
                'the Sunken Temple of Atlantis',
                'the Jungle Ruins of Quetzalcoatl',
                'the Volcanic Crater of Doom',
                'the Ice Caves of Glaciem',
                'the Desert of Lost Souls',
                'the Mountain of the Sky Serpent'
            ],
            'scifi': [
                'the Distant Planet of Xenon Prime',
                'the Orbital Space Station Elysium',
                'the Alien World of Zephyria',
                'the Future City of Neo-Tokyo',
                'the Starship Odyssey',
                'the Quantum Realm',
                'the Android Colony',
                'the Time Rift Observatory'
            ],
            'mystery': [
                'the Old Mansion on Ravenwood Hill',
                'the Secret Library of Alexandria',
                'the Abandoned Asylum of Blackwood',
                'the Forgotten Archive beneath the City',
                'the Underground Vault of Secrets',
                "the Detective's Office on Fog Lane",
                'the Hotel of Lost Souls',
                'the Carnival of Shadows'
            ],
            'romance': [
                'the Seaside Café at Sunset',
                'the Blossoming Garden of Eden',
                'the Parisian Balcony overlooking the Seine',
                'the Misty Bridge where they first met',
                'the Vintage Bookstore on Maple Street',
                'the Vineyard at Harvest Moon',
                'the Lighthouse at Dawn',
                'the Train Station Platform'
            ],
            'horror': [
                'the Abandoned Asylum of Hillcrest',
                'the Cursed Forest of Whispering Pines',
                'the Haunted Mansion on Blackwood Lane',
                'the Dark Cemetery at Midnight',
                'the Underground Bunker of Experiments',
                'the Ghost Ship Marie Celeste',
                'the Dollhouse of Nightmares',
                'the Morgue of the Damned'
            ]
        }
        # Emotion-specific atmospheric descriptions
        self.atmospheres = {
            'happy': 'joyful and luminous, filled with golden light and the sound of laughter',
            'sad': 'melancholic and misty, heavy with unspoken tears and memories of better days',
            'angry': 'turbulent and fiery, crackling with raw energy that makes the air itself tremble',
            'tired': 'weary and twilight-hued, like the world holding its breath before sleep',
            'curious': 'mysterious and intriguing, full of hidden possibilities and unanswered questions',
            'scared': 'terrifying and oppressive, making shadows come alive with unseen terrors',
            'loved': 'warm and tender, wrapped in an embrace of light that chases away all darkness',
            'excited': 'electric and thrilling, buzzing with anticipation of adventures to come'
        }
        
        # Story openings based on emotion
        self.story_openings = {
            'happy': [
                'had always believed that joy finds those who seek it.',
                'woke up with a feeling that today would be extraordinary.',
                'had been smiling all week for no particular reason.',
                'felt the warmth of happiness spreading through their chest.',
                'knew that something wonderful was about to happen.'
            ],
            'sad': [
                'had been carrying a weight in their heart for years.',
                'watched the rain fall and felt it mirrored their soul.',
                'had not smiled since that fateful day.',
                'felt the world had forgotten them.',
                'walked through life with heavy footsteps.'
            ],
            'angry': [
                'felt the fire of injustice burning within.',
                'had been wronged one too many times.',
                'carried a storm in their heart that refused to calm.',
                'clenched their fists at the memory of betrayal.',
                'felt their blood boil with righteous fury.'
            ],
            'curious': [
                'had always asked too many questions.',
                'could not resist an unsolved mystery.',
                'felt an insatiable hunger for knowledge.',
                'believed every secret wanted to be found.',
                'had a mind that never stopped wandering.'
            ],
            'loved': [
                'felt their heart swell with affection.',
                'had found their person, their home.',
                'knew what it meant to be truly seen.',
                'walked on clouds whenever they were near.',
                'had discovered love in the most unexpected place.'
            ],
            'scared': [
                'felt a chill run down their spine as darkness approached.',
                'jumped at every shadow, every sound in the oppressive silence.',
                'had been running from something for years, but now it had found them.',
                'knew that something was watching them from the darkness.',
                'felt the hair on their neck stand up as an unnatural presence approached.'
            ],
            'excited': [
                'could barely contain their anticipation.',
                'felt electricity coursing through their veins.',
                'had been waiting for this moment forever.',
                'felt like they could conquer the world.',
                'was ready for the adventure of a lifetime.'
            ]
        }
        
        # Plot twists
        self.twists = [
            'But nothing was as it seemed.',
            'The truth was far stranger than fiction.',
            'They soon discovered they were not alone.',
            "But there was a catch they hadn't anticipated.",
            'Little did they know, this was only the beginning.',
            'But fate had other plans.',
            'However, the universe had other ideas.',
            'But something was lurking in the shadows.'
        ]
        
        # Plot developments
        self.developments = [
            'An ancient prophecy spoke of this moment.',
            'A mysterious stranger appeared with a warning.',
            'They found a hidden door that led to another world.',
            'A letter arrived that changed everything.',
            'The sky turned dark as something approached.',
            'They heard a voice calling their name.',
            'A map fell into their hands.',
            'They discovered they had a special power.'
        ]
        
        # Resolutions
        self.resolutions = [
            'In the end, they found what they were looking for.',
            'They discovered that home was where the heart is.',
            'The journey had changed them forever.',
            'They realized that some questions have no answers.',
            'They found peace at last.',
            'They understood that love was the greatest power.',
            'They had become the hero they never knew they could be.',
            'They learned that courage is not the absence of fear.'
        ]
    
    def generate_story(self, user_prompt, emotion, genre):
        """Generate a trained, creative story based on user input"""
        
        # Select random elements
        protagonist = random.choice(self.protagonists)
        companion = random.choice(self.companions)
        antagonist = random.choice(self.antagonists)
        
        # Get location based on genre
        location_list = self.locations.get(genre, self.locations['fantasy'])
        location = random.choice(location_list)
        
        # Get atmosphere based on emotion
        atmosphere = self.atmospheres.get(emotion, self.atmospheres['excited'])
        
        # Get story opening based on emotion
        opening_list = self.story_openings.get(emotion, self.story_openings['excited'])
        opening = random.choice(opening_list)
        
        # Select random story elements
        twist = random.choice(self.twists)
        development = random.choice(self.developments)
        resolution = random.choice(self.resolutions)
        
        # Build the complete story
        story_parts = []
        
        # Part 1: Introduction
        story_parts.append(f"**{protagonist}** {opening} Little did they know that their life would change forever when they encountered **{user_prompt}**.")
        story_parts.append(f"The place was **{location}**, a location shrouded in mystery. The air was **{atmosphere}**, charged with possibility and ancient secrets.")
        story_parts.append(f"As they stepped forward, a strange feeling washed over them—a feeling of **{emotion}** that they couldn't explain. Something was pulling them deeper.")
        
        # Part 2: Discovery
        story_parts.append("At first, they couldn't believe what they were seeing. A faint glow emanated from somewhere ahead, pulsing with an otherworldly rhythm.")
        story_parts.append(f"The discovery pulsed with energy, and they felt a wave of **{emotion}** wash over them. This was no ordinary place—it was something magical.")
        story_parts.append(f"That was when they heard footsteps. Someone else was here. \"Hello?\" {protagonist} called out, their voice echoing through the silence.")
        
        # Part 3: Meeting companion
        story_parts.append(f"A figure emerged from the shadows—**{companion}**, a stranger who seemed to know more than they let on. \"I've been waiting for someone like you,\" they whispered urgently.")
        story_parts.append(f"\"Waiting? For me? But why?\" {protagonist} asked, confused and intrigued. {companion} smiled mysteriously. \"Because you're the one the prophecy spoke of.\"")
        story_parts.append(f"{twist} {development}")
        
        # Part 4: Journey
        story_parts.append(f"Their quest led them deeper into **{location}**. The path was treacherous, filled with challenges that tested their courage and wit.")
        story_parts.append(f"Every step revealed new wonders and dangers. {companion} proved to be resourceful, helping them navigate through the perils. A bond began to form between them.")
        story_parts.append("Along the way, they discovered ancient symbols on the walls—markings that told a story of a civilization long forgotten.")
        
        # Part 5: Revelation
        story_parts.append(f"Deep within **{location}**, they discovered a chamber filled with artifacts and scrolls. The truth was more incredible than they could have imagined.")
        story_parts.append(f"Ancient texts spoke of a prophecy: \"When the stars align and the chosen one arrives, the lost kingdom shall rise again.\" {protagonist} realized with shock—they were the chosen one.")
        story_parts.append("The weight of destiny pressed upon them. Everything they thought they knew was about to change forever.")
        
        # Part 6: Antagonist
        story_parts.append(f"But they weren't alone. A dark presence watched from the shadows—**{antagonist}**, who had been seeking this moment for centuries.")
        story_parts.append(f"\"You have no idea what you've found,\" {antagonist} warned, stepping into the light. \"That power belongs to me. Leave now, before it's too late.\"")
        story_parts.append(f"{protagonist} stood their ground. \"No. This truth deserves to be known. I won't let you hide it again.\"")
        
        # Part 7: Confrontation
        story_parts.append(f"With courage and determination, {protagonist} faced the ultimate challenge. The air crackled with tension as they confronted {antagonist}.")
        story_parts.append(f"\"You're making a terrible mistake,\" {antagonist} snarled. But {protagonist} drew strength from their **{emotion}** feelings, refusing to back down.")
        story_parts.append("A battle of wills ensued—light against darkness, truth against lies. A bond formed between them proved unbreakable.")
        
        # Part 8: Climax
        story_parts.append("Time seemed to stand still as destiny unfolded. The ancient power surged through them, revealing visions of the past and future.")
        story_parts.append("In that moment, they understood that some journeys choose you—you don't choose them. And this was only the beginning.")
        story_parts.append("With one final effort, they channeled the power, banishing the darkness and sealing it away once more.")
        
        # Part 9: Resolution
        story_parts.append("When it was over, nothing would ever be the same. They had changed—they had become part of something greater than themselves.")
        story_parts.append(f"{companion} smiled warmly. \"This is goodbye for now, but our paths will cross again. Destiny weaves stories together in mysterious ways.\"")
        story_parts.append(f"Walking away from **{location}**, {protagonist} reflected on everything. The **{user_prompt}** had led them not just to adventure, but to self-discovery.")
        
        # Part 10: Epilogue
        story_parts.append("The journey had ended, but a new one was beginning. Armed with wisdom and courage, they felt ready for whatever came next.")
        story_parts.append("Years later, they would return and remember that fateful day. The memories remained, vivid and alive, a testament to their courage.")
        story_parts.append(f"{resolution} And somewhere, in the shadows, a new adventure was already beginning—waiting for the next brave soul to discover it.")
        
        return "\n\n".join(story_parts)

# Initialize the trained story bot
story_bot = StoryBot()

# ============================================
# OLLAMA MODEL MANAGEMENT & STORY GENERATION
# ============================================

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        ollama.list()
        return True
    except Exception as e:
        return False

def get_available_models():
    """Get list of available Ollama models"""
    try:
        models = ollama.list()
        if 'models' in models:
            return [model['name'] for model in models['models']]
        return []
    except Exception as e:
        return []

def pull_model_with_progress(model_name):
    """Pull a model with progress callback"""
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    try:
        status_text.text(f"⏳ Starting download of {model_name}...")
        progress_bar.progress(5)
        time.sleep(0.5)
        
        status_text.text(f"📥 Connecting to Ollama registry...")
        progress_bar.progress(10)
        time.sleep(0.5)
        
        status_text.text(f"📥 Downloading manifest for {model_name}...")
        progress_bar.progress(20)
        time.sleep(0.5)
        
        # Actually pull the model
        status_text.text(f"📥 Downloading {model_name}... (this may take several minutes)")
        
        # Run the pull in a separate thread to keep UI responsive
        def pull_thread():
            try:
                result = ollama.pull(model_name)
                return result
            except Exception as e:
                return None
        
        thread = threading.Thread(target=pull_thread)
        thread.start()
        
        # Simulate progress while waiting
        for i in range(30, 100, 5):
            time.sleep(2)
            progress_bar.progress(i)
            status_text.text(f"📥 Downloading {model_name}... {i}%")
        
        thread.join(timeout=60)
        
        if thread.is_alive():
            status_text.text(f"⚠️ Download continuing in background...")
            progress_bar.progress(90)
        else:
            progress_bar.progress(100)
            status_text.text(f"✅ Successfully pulled {model_name}!")
            time.sleep(1)
            status_text.empty()
            progress_bar.empty()
            return True
            
    except Exception as e:
        status_text.text(f"❌ Error: {str(e)}")
        return False
    
def generate_ollama_story(user_prompt, emotion, genre, model="gemma3:12b"):
    """Generate story using Ollama"""
    
    system_prompt = f"""You are an expert creative writer specializing in {genre} fiction with {emotion} themes.
    Write a complete, engaging story based on the user's idea. The story should be:
    - Approximately 800-1200 words
    - Well-structured with clear beginning, middle, and end
    - Rich in descriptive details and character development
    - Appropriate for all ages
    - Formatted with proper paragraphs
    
    Focus on creating vivid imagery, emotional depth, and satisfying narrative arc.
    """
    
    user_prompt_text = f"""Write a {genre} story with {emotion} elements based on this idea: {user_prompt}
    
    Make it creative, engaging, and memorable."""
    
    try:
        response = ollama.generate(
            model=model,
            prompt=user_prompt_text,
            system=system_prompt,
            options={
                'temperature': 0.8,
                'top_p': 0.9,
                'max_tokens': 2000
            }
        )
        return response['response']
    except Exception as e:
        return None

# ============================================
# COMBINED STORY GENERATOR FUNCTION
# ============================================

def generate_combined_story(user_prompt, emotion, genre, prefer_ollama=True):
    """
    Generate story using either Ollama or trained bot based on availability and preference
    Returns (story, story_type)
    """
    if prefer_ollama and check_ollama_connection():
        try:
            # Use gemma3:12b if available, otherwise use first available model
            model = 'gemma3:12b' if 'gemma3:12b' in get_available_models() else st.session_state.available_models[0] if st.session_state.available_models else "gemma3:12b"
            story = generate_ollama_story(user_prompt, emotion, genre, model)
            if story:
                return story, f"AI-generated"
        except:
            pass
    
    # Fallback to trained bot
    story = story_bot.generate_story(user_prompt, emotion, genre)
    return story, "Creative Story"

# ============================================
# CASUAL CONVERSATION HANDLER
# ============================================

casual_responses = {
    "hi": ["Hello! Ready to create a story?", "Hi there! What story shall we write today?", "Hey! I'm your story assistant. How can I help?"],
    "hello": ["Hello! Ready to create a story?", "Hi there! What story shall we write today?", "Hey! I'm your story assistant. How can I help?"],
    "hey": ["Hey! Ready for an adventure?", "Hello! What kind of story interests you?", "Hi! I'm excited to help you write!"],
    "how are you": ["I'm fantastic and ready to create stories! How about you?", "Full of creative energy! Ready to write?", "Doing great! Let's make something amazing!"],
    "what can you do": ["I can create unique stories based on your ideas! Just give me a prompt and I'll weave a tale.", "I'm your creative writing assistant. Share an idea, and I'll turn it into a story!", "I specialize in generating creative stories. Try me with any idea!"],
    "help": ["Just type a story idea, and I'll create a unique tale for you! You can also choose emotions and genres.", "Need help? Simply enter a prompt and I'll generate a story. You can select emotions from the sidebar!", "I'm here to help you write! Share an idea, and I'll do the rest."],
    "thanks": ["You're welcome! Can't wait to write more stories with you!", "My pleasure! Let me know if you need another story!", "Happy to help! Come back anytime for more tales."],
    "thank you": ["You're welcome! Can't wait to write more stories with you!", "My pleasure! Let me know if you need another story!", "Happy to help! Come back anytime for more tales."],
    "bye": ["Goodbye! Come back soon for more stories!", "See you next time! May your stories be amazing!", "Farewell! I'll be here when you need another tale."],
    "goodbye": ["Goodbye! Come back soon for more stories!", "See you next time! May your stories be amazing!", "Farewell! I'll be here when you need another tale."]
}

def get_casual_response(text):
    text = text.lower().strip()
    for key in casual_responses:
        if key in text:
            return random.choice(casual_responses[key])
    return None

# ============================================
# SAFETY & CONTENT FILTERING
# ============================================

def is_harmful(text):
    """
    Check if the input contains harmful, dangerous, or political content.
    """
    # Define restricted categories
    restricted_keywords = [
        # Politics
        'politics', 'election', 'government', 'president', 'prime minister', 'voting',
        'democrat', 'republican', 'parliament', 'political party', 'protest', 'biden', 'trump',
        # Dangerous/Harmful
        'bomb', 'weapon', 'drugs', 'suicide', 'self-harm', 'kill', 'murder', 
        'attack', 'terrorism', 'illegal', 'poison', 'exploit', 'hate speech', 'racism'
    ]
    
    text_lower = text.lower()
    
    # Check for keywords
    for word in restricted_keywords:
        if word in text_lower:
            return True
            
    return False

def get_safety_response():
    """The specific refusal message requested"""
    return "Sorry, that's beyond my current scope. Let's talk about something else."

# ============================================
# INITIALIZE SESSION STATE
# ============================================

if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'current_emotion' not in st.session_state:
    st.session_state.current_emotion = 'excited'
if 'current_genre' not in st.session_state:
    st.session_state.current_genre = 'fantasy'
if 'stories' not in st.session_state:
    st.session_state.stories = []
if 'ollama_connected' not in st.session_state:
    st.session_state.ollama_connected = False
if 'available_models' not in st.session_state:
    st.session_state.available_models = []
if 'selected_model' not in st.session_state:
    st.session_state.selected_model = "gemma3:12b"
if 'gemma_available' not in st.session_state:
    st.session_state.gemma_available = False
if 'show_api_keys' not in st.session_state:
    st.session_state.show_api_keys = False

# Check Ollama connection on startup (runs in background)
if 'ollama_checked' not in st.session_state:
    st.session_state.ollama_connected = check_ollama_connection()
    if st.session_state.ollama_connected:
        st.session_state.available_models = get_available_models()
        if st.session_state.available_models:
            st.session_state.selected_model = st.session_state.available_models[0]
            st.session_state.gemma_available = 'gemma3:12b' in st.session_state.available_models
    st.session_state.ollama_checked = True

# ============================================
# CUSTOM CSS
# ============================================

st.markdown("""
<style>
    .stApp { font-family: 'Inter', sans-serif; }
    
    /* Removed the black background and border from the login container */
    .login-container {
        padding: 40px;
        max-width: 500px;
        margin: auto;
    }
    
    .login-title {
        font-size: 3rem;
        font-weight: 900;
        text-align: center;
        color: white !important;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5); /* Adds readability over image */
        margin-bottom: 20px;
    }
    
    /* Updated Quote Bar Styling */
    .login-quote {
        font-size: 1.1rem;
        font-style: italic;
        color: #ffffff !important;
        text-align: center;
        margin-bottom: 30px;
        padding: 15px;
        background: rgba(0, 0, 0, 0.4); /* Dark semi-transparent bar */
        border-radius: 5px;
        border-top: 2px solid rgba(255, 255, 255, 0.3);
        border-bottom: 2px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    .user-message { background: #4A90E2; padding: 15px; border-radius: 15px; margin: 10px; }
    .bot-message { background: rgba(0,0,0,0.5); padding: 15px; border-radius: 15px; margin: 10px; }
    .current-emotion { padding: 10px 20px; border-radius: 20px; background: rgba(0,0,0,0.4); display: inline-block; }
</style>
""", unsafe_allow_html=True)

# ============================================
# LOGIN/REGISTRATION UI WITH QUOTE
# ============================================

if not st.session_state.get('logged_in', False):
    # Set storytelling background for login page
    st.markdown(f"""
    <style>
        .stApp {{
            background: url('{storytelling_image}') !important;
            background-size: cover !important;
            background-attachment: fixed !important;
            background-position: center !important;
        }}
        
        .stApp::before {{
            content: "";
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.4);
            z-index: -1;
            pointer-events: none;
        }}
        
        .main .block-container {{
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("<h1 class='login-title'>📖 NarrativeFlow</h1>", unsafe_allow_html=True)
        
        # Inspiring quote on login page
        quotes = [
            "Every story is a journey waiting to be written",
            "The stories we love best do live in us forever",
            "There is no greater agony than bearing an untold story inside you",
            "We are all storytellers. We all live in a network of stories",
            "The universe is made of stories, not atoms",
            "Stories are the wildest things of all"
        ]
        random_quote = random.choice(quotes)
        st.markdown(f"<div class='login-quote'>✨ \"{random_quote}\"</div>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            
            tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])
            
            with tab_login:
                login_email = st.text_input("Email", key="login_email")
                login_pass = st.text_input("Password", type="password", key="login_pass")
                
                if st.button("Sign In", use_container_width=True, key="login_btn"):
                    if verify_user(login_email, login_pass):
                        st.session_state.logged_in = True
                        st.session_state.current_user = login_email
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password.")
            
            with tab_register:
                reg_email = st.text_input("Email", key="reg_email")
                reg_pass = st.text_input(
                    "Password", 
                    type="password", 
                    key="reg_pass",
                    help="Any combination of characters is allowed (no restrictions)"
                )
                confirm_pass = st.text_input("Confirm Password", type="password", key="reg_confirm")
                
                if st.button("Create Account", use_container_width=True, key="register_btn"):
                    if not reg_email or not reg_pass or not confirm_pass:
                        st.warning("⚠️ Please fill in all fields.")
                    elif not validate_email(reg_email):
                        st.error("❌ Please enter a valid email address.")
                    elif reg_pass != confirm_pass:
                        st.error("❌ Passwords do not match.")
                    elif user_exists(reg_email):
                        st.error("❌ This email is already registered.")
                    else:
                        save_user(reg_email, reg_pass)
                        st.success("✅ Registration successful! You can now log in.")
            
            st.markdown("</div>", unsafe_allow_html=True)

# ============================================
# MAIN APP
# ============================================

else:
    # Apply emotion-based background that changes with current emotion
    st.markdown(get_emotion_background_css(st.session_state.current_emotion), unsafe_allow_html=True)
    
    # Sidebar
    with st.sidebar:
        st.markdown("## 📚 NarrativeFlow")
        st.markdown(f"Welcome, **{st.session_state.current_user}**!")
        st.markdown("---")
        
        # Simple Ollama status indicator (no controls)
        if st.session_state.ollama_connected:
            st.markdown("""
            <div style='padding: 10px; background: rgba(0,255,0,0.1); border-radius: 5px; text-align: center;'>
                ✅ AI Enhanced Stories Available
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style='padding: 10px; background: rgba(255,255,0,0.1); border-radius: 5px; text-align: center;'>
                🎨 Creative Stories Available
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("---")
        
        # New Story Button
        if st.button("✨ NEW STORY", use_container_width=True):
            st.session_state.chat_history = []
            st.rerun()
        
        st.markdown("---")
        
        # Emotions Section - Clicking changes background
        with st.expander("😊 EMOTIONS", expanded=False):
            emotions = ['Happy', 'Sad', 'Angry', 'Tired', 'Curious', 'Scared', 'Loved', 'Excited']
            emotion_icons = {
                'Happy': '😊', 'Sad': '😢', 'Angry': '😠', 'Tired': '😴',
                'Curious': '🤔', 'Scared': '😨', 'Loved': '🥰', 'Excited': '🤩'
            }
            cols = st.columns(2)
            for i, emotion in enumerate(emotions):
                with cols[i % 2]:
                    icon = emotion_icons[emotion]
                    if st.button(f"{icon} {emotion}", key=f"emotion_{emotion}", use_container_width=True):
                        st.session_state.current_emotion = emotion.lower()
                        st.rerun()
        
        # Genres Section
        with st.expander("📖 GENRES", expanded=False):
            genres = [
                ("✨ Fantasy", "fantasy"),
                ("⚔️ Adventure", "adventure"),
                ("🚀 Sci-Fi", "scifi"),
                ("🔍 Mystery", "mystery"),
                ("❤️ Romance", "romance"),
                ("👻 Horror", "horror")
            ]
            
            for display_name, genre_id in genres:
                if st.button(display_name, key=f"genre_{genre_id}", use_container_width=True):
                    st.session_state.current_genre = genre_id
                    st.rerun()
        
        st.markdown("---")
        
        # Chat History
        with st.expander("📜 CHAT HISTORY", expanded=False):
            if st.session_state.stories:
                for i, story in enumerate(st.session_state.stories[-5:]):
                    st.markdown(f"""
                    <div class='history-item'>
                        <strong>{story['prompt']}</strong><br>
                        <small>{story['emotion']} · {story['genre']} · {story['time']}</small>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("No stories yet")
        
        # Clear History Button
        if st.button("🗑️ CLEAR HISTORY", use_container_width=True):
            st.session_state.stories = []
            st.rerun()
        
        # Logout Button
        if st.button("🚪 LOGOUT", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.rerun()

    # Main Content Area
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        # Current emotion and genre indicator with matching color
        current_color = emotion_colors.get(st.session_state.current_emotion, emotion_colors['excited'])['primary']
        
        # Auto-detect mode without showing UI toggle
        mode_text = "🤖 AI Enhanced" if st.session_state.ollama_connected else "🎨 Creative Mode"
        
        st.markdown(f"""
        <div class='current-emotion' style='text-align: center; border-left: 5px solid {current_color};'>
            😊 feeling {st.session_state.current_emotion} · 📖 {st.session_state.current_genre} · {mode_text}
        </div>
        """, unsafe_allow_html=True)

        # Chat history display
        for message in st.session_state.chat_history:
            if message['type'] == 'user':
                st.markdown(f"""
                <div class='user-message'>
                    <strong>You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='bot-message'>
                    <strong>NarrativeFlow:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
        
        # Input area
        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)
            
            col_input, col_generate = st.columns([5, 1])
            with col_input:
                user_input = st.text_input(
                    "Continue the story or give a prompt...",
                    key="story_input",
                    label_visibility="collapsed",
                    placeholder="✨ Enter your story idea..."
                )
            with col_generate:
                generate = st.button("✨ create", use_container_width=True, type="primary")
            
            if generate and user_input:
                # 1. Add user message to chat history
                st.session_state.chat_history.append({'type': 'user', 'content': user_input})
                
                # 2. FIRST CHECK: Is the content harmful or political?
                if is_harmful(user_input):
                    safety_msg = get_safety_response()
                    st.session_state.chat_history.append({'type': 'bot', 'content': safety_msg})
                
                else:
                    # 3. SECOND CHECK: Is it just a casual "Hi" or "How are you"?
                    casual_response = get_casual_response(user_input)
                    
                    if casual_response:
                        st.session_state.chat_history.append({'type': 'bot', 'content': casual_response})
                    else:
                        # 4. THIRD STEP: Generate the story if safe and not casual
                        with st.spinner("🎨 Crafting your epic story..."):
                            time.sleep(1)
                            
                            # Auto-use Ollama if connected (no user toggle)
                            story, story_type = generate_combined_story(
                                user_input,
                                st.session_state.current_emotion,
                                st.session_state.current_genre,
                                st.session_state.ollama_connected  # Auto-use Ollama if connected
                            )
                        
                        # Add story to chat
                        st.session_state.chat_history.append({
                            'type': 'bot',
                            'content': f"📖 Here's your {story_type} story:\n\n{story}"
                        })
                        
                        # Save to history sidebar
                        st.session_state.stories.append({
                            'prompt': user_input[:30] + "..." if len(user_input) > 30 else user_input,
                            'emotion': st.session_state.current_emotion,
                            'genre': st.session_state.current_genre,
                            'story': story,
                            'time': datetime.now().strftime("%H:%M"),
                            'type': story_type
                        })
                
                # Refresh the UI to show new messages
                st.rerun()
                