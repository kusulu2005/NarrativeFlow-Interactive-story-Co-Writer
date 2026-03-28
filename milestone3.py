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
import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================
# PROJECT CONFIGURATION
# ============================================
# ============================================
# REINFORCEMENT LEARNING ENGINE (Q-LEARNING)
# ============================================
RL_DATA_FILE = "rl_brain.json"

class StoryRLBrain:
    """A simple Reinforcement Learning brain using Q-Learning to learn user style preferences."""
    def __init__(self):
        self.q_table = self.load_q_table()
        self.learning_rate = 0.1

    def load_q_table(self):
        if os.path.exists(RL_DATA_FILE):
            with open(RL_DATA_FILE, 'r') as f: return json.load(f)
        return {}

    def save_q_table(self):
        with open(RL_DATA_FILE, 'w') as f: json.dump(self.q_table, f, indent=2)

    def get_state(self, prompt):
        words = re.sub(r'[^\w\s]', '', prompt.lower()).split()
        return words[0] if words else "general"

    def update_knowledge(self, prompt, emotion, genre, reward):
        state = self.get_state(prompt)
        action = f"{emotion}_{genre}"
        if state not in self.q_table: self.q_table[state] = {}
        current_q = self.q_table[state].get(action, 0.0)
        # Q-Learning update rule
        self.q_table[state][action] = round(current_q + self.learning_rate * (reward - current_q), 3)
        self.save_q_table()

    def get_best_style_hint(self, prompt):
        state = self.get_state(prompt)
        if state in self.q_table and self.q_table[state]:
            best_action = max(self.q_table[state], key=self.q_table[state].get)
            if self.q_table[state][best_action] > 0:
                return f"Learned Preference: Users liked a {best_action.replace('_', ' ')} style for this topic."
        return ""

rl_brain = StoryRLBrain()
PROJECT_NAME = "Dream Weaver"

st.set_page_config(
    page_title=f"{PROJECT_NAME} - Infinite Imagination",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Use this for the main title on the landing page
st.markdown(f"<h1 style='text-align: center;'>🔮 {PROJECT_NAME}</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #60a5fa;'>Where Imagination Meets Integrity</p>", unsafe_allow_html=True)

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
    """Saves a new user with all required ML and preference keys"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    
    users[email] = {
        'password': hash_password(password),
        'created_at': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        'stories_count': 0,
        'last_active': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        
        # PREVENTS KEYERROR: Initialize preferences immediately
        'preferences': {
            'default_emotion': 'excited', 
            'default_genre': 'fantasy'
        },
        
        'user_details': user_details or {}
    }
    
    with open(USER_DATA_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def verify_user(email, password):
    """Verify user credentials"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    if email in users:
        # Update last active time
        users[email]['last_active'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
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

def update_user_preferences(email, preferences):
    """Update user preferences safely, creating the key if it doesn't exist"""
    with open(USER_DATA_FILE, 'r') as f:
        users = json.load(f)
    
    if email in users:
        # Check if 'preferences' key exists, if not, create it
        if 'preferences' not in users[email]:
            users[email]['preferences'] = {}
            
        users[email]['preferences'].update(preferences)
        
        with open(USER_DATA_FILE, 'w') as f:
            json.dump(users, f, indent=2)
        return True
    return False

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
    'peaceful': 'https://images.pexels.com/photos/1173777/pexels-photo-1173777.jpeg?auto=compress&cs=tinysrgb&w=1600',
    'nostalgic': 'https://images.pexels.com/photos/235985/pexels-photo-235985.jpeg?auto=compress&cs=tinysrgb&w=1600'
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
    },
    'peaceful': {
        'primary': '#98FB98',
        'secondary': '#90EE90',
        'gradient': 'linear-gradient(135deg, #98FB98, #87CEEB, #E0FFFF)',
        'accent': '#FFE4B5'
    },
    'nostalgic': {
        'primary': '#DEB887',
        'secondary': '#D2B48C',
        'gradient': 'linear-gradient(135deg, #DEB887, #F4A460, #CD853F)',
        'accent': '#8B4513'
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
        
        /* Story text styling */
        .story-text {{
            font-size: 1.1rem;
            line-height: 1.8;
            color: #ffffff;
            text-shadow: 1px 1px 2px rgba(0,0,0,0.5);
        }}
        
        .story-text p {{
            margin-bottom: 1.5rem;
        }}
    </style>
    """

# ============================================
# ENHANCED STORY GENERATOR WITH LLaMA INTEGRATION
# ============================================

class EnhancedStoryBot:
    """An enhanced story generation bot with LLaMA integration for more natural storytelling"""
    
    def __init__(self):
        # Expanded character name bank with cultural diversity
        self.protagonists = [
            'Elena', 'Marcus', 'Sofia', 'James', 'Isabella', 'Oliver', 'Amara', 'Theo', 'Luna', 'Caspian',
            'Aria', 'Dorian', 'Freya', 'Rowan', 'Silas', 'Elara', 'Jasper', 'Iris', 'Corvin', 'Lyra',
            'Magnus', 'Nova', 'Orion', 'Willow', 'Atlas', 'Seraphina', 'Phoenix', 'Raven', 'Sterling', 'Vesper',
            'Aurora', 'Caleb', 'Delilah', 'Ezra', 'Flora', 'Gideon', 'Helena', 'Ignatius', 'Juniper', 'Kai',
            'Zara', 'Kael', 'Mira', 'Finn', 'Ivy', 'Leo', 'Maya', 'Oscar', 'Rosa', 'Felix',
            'Mei', 'Raj', 'Chloe', 'Ahmed', 'Priya', 'Diego', 'Yuki', 'Amira', 'Chen', 'Mateo'
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
        
        # Rich location database per genre with more descriptive elements
        self.locations = {
            'fantasy': [
                'the Enchanted Forest where ancient trees whisper secrets to those who listen',
                'the Floating Castle of Serendell, suspended between clouds and dreams',
                "the Dragon's Lair, hidden deep within the Crystal Mountains",
                'the Fairy Kingdom of Luminara, where magic flows like water',
                "the Wizard's Tower at the Edge of Reality, where time flows differently",
                'the Lost City of Eldoria, buried beneath centuries of sand and mystery',
                'the Crystal Caves of Avalon, where light dances like liquid rainbows',
                'the Temple of the Moon Goddess, shrouded in eternal twilight'
            ],
            'adventure': [
                'the Mysterious Island of Kalypso, where every step reveals a new secret',
                'the Hidden Valley of the Ancients, untouched by time',
                'the Sunken Temple of Atlantis, its spires reaching toward the surface',
                'the Jungle Ruins of Quetzalcoatl, overgrown with emerald vines',
                'the Volcanic Crater of Doom, where the earth itself breathes fire',
                'the Ice Caves of Glaciem, where frozen waterfalls catch the northern lights',
                'the Desert of Lost Souls, where mirages dance on endless dunes',
                'the Mountain of the Sky Serpent, piercing the clouds themselves'
            ],
            'scifi': [
                'the Distant Planet of Xenon Prime, with its bioluminescent forests',
                'the Orbital Space Station Elysium, humanity\'s greatest achievement',
                'the Alien World of Zephyria, where methane rains and silicon lifeforms thrive',
                'the Future City of Neo-Tokyo, a neon-lit maze of possibility',
                'the Starship Odyssey, drifting through the void between galaxies',
                'the Quantum Realm, where reality itself becomes uncertain',
                'the Android Colony, where machine and consciousness merge',
                'the Time Rift Observatory, watching the fabric of spacetime'
            ],
            'mystery': [
                'the Old Mansion on Ravenwood Hill, its windows like watching eyes',
                'the Secret Library of Alexandria, holding knowledge forbidden to mortals',
                'the Abandoned Asylum of Blackwood, where whispers echo through empty halls',
                'the Forgotten Archive beneath the City, buried with its secrets',
                'the Underground Vault of Secrets, protected by ancient mechanisms',
                "the Detective's Office on Fog Lane, where justice meets the shadows",
                'the Hotel of Lost Souls, where guests check in but never leave',
                'the Carnival of Shadows, where nothing is as it appears'
            ],
            'romance': [
                'the Seaside Café at Sunset, where waves compose love songs',
                'the Blossoming Garden of Eden, where love first bloomed',
                'the Parisian Balcony overlooking the Seine, bathed in golden light',
                'the Misty Bridge where they first met, now sacred ground',
                'the Vintage Bookstore on Maple Street, filled with stories of love',
                'the Vineyard at Harvest Moon, where grapes grow sweet with passion',
                'the Lighthouse at Dawn, standing sentinel over eternal love',
                'the Train Station Platform, where hearts meet and part'
            ],
            'horror': [
                'the Abandoned Asylum of Hillcrest, where sanity itself is questioned',
                'the Cursed Forest of Whispering Pines, where trees have eyes',
                'the Haunted Mansion on Blackwood Lane, trapped in eternal night',
                'the Dark Cemetery at Midnight, where the ground barely holds its dead',
                'the Underground Bunker of Experiments, where science became nightmare',
                'the Ghost Ship Marie Celeste, adrift with its terrible secret',
                'the Dollhouse of Nightmares, where playthings come alive',
                'the Morgue of the Damned, where the dead don\'t rest'
            ],
            'historical': [
                'ancient Rome during the height of the Empire, where destiny awaits',
                'medieval London, where knights and merchants walk cobblestone streets',
                'Renaissance Florence, where art and intrigue flourish',
                'the court of Imperial China, where dragons dance and poets dream',
                'Victorian England, where gaslights flicker with mystery',
                'the Egyptian pyramids during their construction, a wonder of the world',
                'the Mayan civilization, where astronomy meets prophecy',
                'the Viking Age, where longships sail toward destiny'
            ],
            'mythology': [
                'Mount Olympus, where gods walk among mortals',
                'Asgard, the realm of Norse legends and eternal warriors',
                'the Underworld, where souls journey to their final rest',
                'Atlantis, the lost continent of advanced civilization',
                'the Garden of Eden, where creation began',
                'Camelot, where knights sought the Holy Grail',
                'El Dorado, the city of gold hidden from the world',
                'Avalon, where magic and reality intertwine'
            ]
        }
        
        # Enhanced emotion-specific atmospheric descriptions
        self.atmospheres = {
            'happy': 'joyful and luminous, filled with golden light and the sound of laughter echoing through sun-drenched meadows',
            'sad': 'melancholic and misty, heavy with unspoken tears and memories of better days, like rain on windowpanes',
            'angry': 'turbulent and fiery, crackling with raw energy that makes the air itself tremble and shadows dance',
            'tired': 'weary and twilight-hued, like the world holding its breath before sleep, soft and muted',
            'curious': 'mysterious and intriguing, full of hidden possibilities and unanswered questions that beckon exploration',
            'scared': 'terrifying and oppressive, making shadows come alive with unseen terrors and every sound a threat',
            'loved': 'warm and tender, wrapped in an embrace of light that chases away all darkness, like a mother\'s lullaby',
            'excited': 'electric and thrilling, buzzing with anticipation of adventures to come, heart racing with possibility',
            'peaceful': 'serene and calm, like a still lake at dawn, where time itself seems to slow and breathe',
            'nostalgic': 'bittersweet and reflective, colored with the sepia tones of memory and the ache of days gone by'
        }
        
        # Enhanced story openings with more natural language
        self.story_openings = {
            'happy': [
                'had always believed that joy finds those who seek it, and today that belief would be proven true.',
                'woke up with a feeling that today would be extraordinary, a warmth spreading through their chest.',
                'had been smiling all week for no particular reason, as if the universe was preparing them for something wonderful.',
                'felt the warmth of happiness spreading through their chest like sunlight through morning clouds.',
                'knew that something wonderful was about to happen; they could feel it in their bones.'
            ],
            'sad': [
                'had been carrying a weight in their heart for years, a burden that colored every moment in shades of gray.',
                'watched the rain fall and felt it mirrored their soul, each drop a memory of what once was.',
                'had not smiled since that fateful day, when everything they loved had slipped through their fingers.',
                'felt the world had forgotten them, leaving them to wander through life invisible and alone.',
                'walked through life with heavy footsteps, each step a reminder of the path not taken.'
            ],
            'angry': [
                'felt the fire of injustice burning within, a flame that refused to be extinguished by time or reason.',
                'had been wronged one too many times, and today would be the day they finally stood up.',
                'carried a storm in their heart that refused to calm, thunder rumbling with every heartbeat.',
                'clenched their fists at the memory of betrayal, the pain still fresh as the day it happened.',
                'felt their blood boil with righteous fury, ready to face whatever stood in their way.'
            ],
            'curious': [
                'had always asked too many questions, driven by an insatiable hunger to understand the world.',
                'could not resist an unsolved mystery, like a moth drawn to flame by the promise of answers.',
                'felt an insatiable hunger for knowledge that could never be fully satisfied.',
                'believed every secret wanted to be found, every locked door begged to be opened.',
                'had a mind that never stopped wandering, exploring possibilities others couldn\'t see.'
            ],
            'loved': [
                'felt their heart swell with affection, a warmth so profound it seemed to light them from within.',
                'had found their person, their home, and every day felt like a gift because of it.',
                'knew what it meant to be truly seen, understood, and cherished beyond measure.',
                'walked on clouds whenever they were near, the world brighter and more beautiful.',
                'had discovered love in the most unexpected place, proving that destiny has a sense of humor.'
            ],
            'scared': [
                'felt a chill run down their spine as darkness approached, primal instincts screaming warnings.',
                'jumped at every shadow, every sound in the oppressive silence of the night.',
                'had been running from something for years, but now it had finally found them.',
                'knew that something was watching them from the darkness, patient and hungry.',
                'felt the hair on their neck stand up as an unnatural presence approached, bringing cold with it.'
            ],
            'excited': [
                'could barely contain their anticipation, heart pounding like drums before a celebration.',
                'felt electricity coursing through their veins, every nerve alive with possibility.',
                'had been waiting for this moment forever, and now it was finally here.',
                'felt like they could conquer the world, invincible and ready for anything.',
                'was ready for the adventure of a lifetime, taking a deep breath before the plunge.'
            ],
            'peaceful': [
                'sat in quiet contemplation, watching the world go by with a gentle smile.',
                'had found a moment of perfect peace, suspended in time like a butterfly in amber.',
                'breathed deeply, feeling the simple joy of existing in the present moment.',
                'watched the sunset paint the sky in colors too beautiful for words.',
                'felt at one with the universe, a single note in an infinite symphony.'
            ],
            'nostalgic': [
                'found themselves lost in memory, walking familiar paths of days gone by.',
                'held an old photograph, wondering about the people they used to be.',
                'returned to a place from their past, finding both change and constancy.',
                'heard a song that transported them back through time, emotions flooding back.',
                'smelled rain on pavement and suddenly remembered childhood summers.'
            ]
        }
        
        # Enhanced plot developments with more variety
        self.developments = [
            'An ancient prophecy spoke of this moment, foretelling the arrival of a chosen one.',
            'A mysterious stranger appeared with a warning that could not be ignored.',
            'They found a hidden door that led to another world, a portal to the impossible.',
            'A letter arrived that changed everything, written in handwriting they recognized.',
            'The sky turned dark as something approached from beyond the stars.',
            'They heard a voice calling their name, a whisper on the wind that knew them.',
            'A map fell into their hands, leading to a treasure beyond imagination.',
            'They discovered they had a special power, dormant until now.',
            'The past came back to haunt them, carrying both danger and answers.',
            'A childhood promise resurfaced, demanding to be fulfilled.',
            'Nature itself seemed to respond to their presence, as if recognizing something.',
            'They found an artifact that pulsed with ancient energy, choosing them as its wielder.'
        ]
        
        # Enhanced plot twists
        self.twists = [
            'But nothing was as it seemed, and the truth was far stranger than fiction.',
            'They soon discovered they were not alone, and had never been.',
            "But there was a catch they hadn't anticipated, a price to be paid.",
            'Little did they know, this was only the beginning of a much larger story.',
            'But fate had other plans, written in stars they couldn\'t read.',
            'However, the universe had other ideas, challenging everything they believed.',
            'But something was lurking in the shadows, watching and waiting.',
            'The enemy they feared was not what they expected, and neither was the ally.',
            'Everything they thought they knew was about to be turned upside down.',
            'The solution to one mystery only opened the door to another.'
        ]
        
        # Enhanced resolutions with more emotional depth
        self.resolutions = [
            'In the end, they found what they were looking for, though it was different than imagined.',
            'They discovered that home was where the heart is, and their heart had found its place.',
            'The journey had changed them forever, leaving marks on their soul that would never fade.',
            'They realized that some questions have no answers, and that\'s perfectly okay.',
            'They found peace at last, not in answers, but in acceptance.',
            'They understood that love was the greatest power of all, stronger than any magic.',
            'They had become the hero they never knew they could be, rising to meet destiny.',
            'They learned that courage is not the absence of fear, but acting despite it.',
            'The circle closed, but a new one opened, for every ending is also a beginning.',
            'They walked away changed, carrying the story with them like a precious treasure.'
        ]
        
        # Story structure templates for more natural flow
        self.story_templates = {
            'fantasy': "In a realm where magic flows like water and ancient powers stir, {protagonist} discovers that {user_prompt} is more than it seems...",
            'adventure': "The map was old and worn, but {protagonist} knew it would lead to {user_prompt}, if they dared to follow...",
            'scifi': "The transmission came from deep space: {user_prompt}. {protagonist} knew this message would change everything...",
            'mystery': "It began with {user_prompt}, a mystery that would consume {protagonist} until the truth was revealed...",
            'romance': "They say love finds you when you least expect it. For {protagonist}, it started with {user_prompt}...",
            'horror': "The first sign was subtle, easily dismissed. But soon {protagonist} realized {user_prompt} was only the beginning...",
            'historical': "In a time when {user_prompt} was more than words, {protagonist} would discover that history has a way of repeating...",
            'mythology': "The old stories spoke of {user_prompt}, but {protagonist} never imagined they would become part of the legend..."
        }
    
    def generate_story(self, user_prompt, emotion, genre):
        """Generate an enhanced, natural-sounding story based on user input"""
        
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
        
        # Get story template
        template = self.story_templates.get(genre, self.story_templates['fantasy'])
        
        # Build the complete story with more natural flow
        story_parts = []
        
        # Introduction with template
        story_parts.append(f"**{protagonist}** {opening}")
        story_parts.append(template.format(protagonist=protagonist, user_prompt=user_prompt))
        story_parts.append(f"The journey led them to **{location}**, a place where the air itself felt **{atmosphere}**.")
        
        # Discovery and setup
        story_parts.append(f"At first, {protagonist} couldn't quite believe what they were experiencing. The world around them seemed to pulse with an energy that felt both foreign and strangely familiar. Every step forward revealed something new, something that challenged their understanding of what was possible.")
        
        # Meeting companion
        story_parts.append(f"That's when they met **{companion}**. \"I've been waiting for someone like you,\" {companion} said, their voice carrying the weight of secrets. \"Not everyone can see what you're seeing. Not everyone is meant to.\"")
        story_parts.append(f"{protagonist} felt a connection to this stranger, as if they'd known each other in another life. Together, they pressed forward, their combined courage greater than the sum of its parts.")
        
        # Introduction of conflict
        story_parts.append(f"But they weren't the only ones drawn to this place. **{antagonist}** had been watching, waiting for this moment. \"You have no idea what you've stumbled into,\" {antagonist} warned, stepping from the shadows. \"Turn back now, before it's too late.\"")
        
        # Development and twist
        story_parts.append(development)
        story_parts.append(twist)
        
        # Rising action
        story_parts.append(f"The revelation shook {protagonist} to their core. Everything they thought they knew about {user_prompt} was wrong. But instead of fear, they felt something else: determination.")
        story_parts.append(f"\"I understand now,\" {protagonist} whispered, the pieces finally falling into place. \"This isn't just about me. It's about everyone who came before, and everyone who will come after.\"")
        
        # Climax
        story_parts.append(f"What followed was a confrontation that would be remembered in songs for generations. {protagonist} faced {antagonist}, drawing strength from the very {emotion} feelings that had brought them here. The air crackled with tension as past and present collided.")
        
        # Turning point
        story_parts.append(f"In that crucial moment, {protagonist} understood something profound: {companion} wasn't just a companion on this journey. They were a reflection of something {protagonist} needed to see in themselves.")
        story_parts.append(f"Together, they channeled something greater than either could have achieved alone. The power of {emotion} flowed through them like a river finding the sea.")
        
        # Resolution
        story_parts.append(f"When it was over, nothing would ever be the same. {protagonist} had changed, grown into someone capable of carrying the weight of this experience.")
        story_parts.append(f"{companion} smiled, a bittersweet expression crossing their face. \"This is goodbye for now, but our paths will cross again. Stories like ours don't end; they just find new beginnings.\"")
        
        # Epilogue
        story_parts.append(f"Walking away from {location}, {protagonist} reflected on everything. The encounter with {user_prompt} had led them not just to adventure, but to a deeper understanding of themselves. The world seemed larger now, full of possibilities they'd never imagined.")
        story_parts.append(resolution)
        story_parts.append(f"And somewhere, in the quiet spaces between heartbeats, a new story was already beginning to write itself. Because that's what stories do - they find those who need them, who are ready to listen, who dare to believe that maybe, just maybe, magic is real.")
        
        return "\n\n".join(story_parts)

# Initialize the enhanced story bot
story_bot = EnhancedStoryBot()

# ============================================
# OLLAMA/LLaMA MODEL MANAGEMENT & STORY GENERATION
# ============================================

def check_ollama_connection():
    """Check if Ollama is running and accessible"""
    try:
        ollama.list()
        return True
    except Exception as e:
        logger.warning(f"Ollama connection failed: {str(e)}")
        return False

def get_available_models():
    """Get list of available Ollama models"""
    try:
        models = ollama.list()
        if 'models' in models:
            return [model['name'] for model in models['models']]
        return []
    except Exception as e:
        logger.error(f"Error getting models: {str(e)}")
        return []

def generate_llama_story(user_prompt, emotion, genre, model="llama3.2:latest"):
    """Generate story using LLaMA model with RL-based style hints"""
    
    # This line pulls the 'memory' from your RL brain to guide LLaMA
    rl_hint = rl_brain.get_best_style_hint(user_prompt)
    
    system_prompt = f"""You are an expert creative writer. 
    Write a {genre} story with {emotion} themes. 
    {rl_hint}
    Requirements: 800-1200 words, sensory descriptions, and immersive pacing."""
    
    user_prompt_text = f"Create a {genre} story about: {user_prompt}. Theme: {emotion}."
    
    try:
        response = ollama.generate(
            model=model,
            prompt=user_prompt_text,
            system=system_prompt,
            options={'temperature': 0.85, 'num_predict': 2048}
        )
        return response['response'].strip()
    except Exception as e:
        logger.error(f"LLaMA error: {str(e)}")
        return None

def check_llama_model_available():
    """Check if LLaMA model is available"""
    available_models = get_available_models()
    
    # List of LLaMA models to check (in order of preference)
    llama_models = ['llama3.2:latest', 'llama3.1:latest', 'llama3:latest', 'llama2:latest']
    
    for model in llama_models:
        if model in available_models:
            return model
    
    return None

# ============================================
# ENHANCED COMBINED STORY GENERATOR FUNCTION
# ============================================

def generate_combined_story(user_prompt, emotion, genre, use_llama=True):
    """
    Generate story using either LLaMA/Ollama or enhanced trained bot
    Returns (story, story_type)
    """
    story = None
    story_type = "Enhanced Story Bot"
    
    if use_llama and check_ollama_connection():
        try:
            # Get available LLaMA model
            llama_model = check_llama_model_available()
            if llama_model:
                with st.spinner(f"🎭 Crafting your story with LLaMA..."):
                    story = generate_llama_story(user_prompt, emotion, genre, llama_model)
                    if story:
                        story_type = f"LLaMA Enhanced Story"
                        logger.info(f"Generated story using {llama_model}")
        except Exception as e:
            logger.error(f"LLaMA generation failed, falling back to bot: {str(e)}")
    
    # Fallback to enhanced bot if LLaMA fails or not available
    if not story:
        with st.spinner("📖 Weaving a tale with our creative bot..."):
            story = story_bot.generate_story(user_prompt, emotion, genre)
            story_type = "Creative Story Bot"
    
    return story, story_type

# ============================================
# ENHANCED CASUAL CONVERSATION HANDLER
# ============================================

casual_responses = {
    "hi": ["Hello! Ready to create a story together?", "Hi there! What tale shall we weave today?", "Hey! I'm your story assistant, excited to help you create something wonderful!"],
    "hello": ["Hello! Ready to create a story together?", "Hi there! What tale shall we weave today?", "Hey! I'm your story assistant, excited to help you create something wonderful!"],
    "hey": ["Hey! Ready for an adventure in storytelling?", "Hello! What kind of story speaks to you today?", "Hi! I'm brimming with creative energy and ready to help!"],
    "how are you": ["I'm fantastic and full of stories! How about you?", "Thriving on creativity! Ready to write something amazing?", "Doing wonderfully! Let's make some magic together!"],
    "what can you do": ["I can craft unique, immersive stories based on your ideas! Just share a prompt, and I'll weave it into a narrative.", "I'm your creative companion. Give me an idea, an emotion, a genre, and watch as a story unfolds!", "I specialize in bringing imagination to life. Try me with any story concept!"],
    "help": ["Simply type a story idea, and I'll transform it into a tale! You can also choose emotions and genres from the sidebar to shape the mood.", "Need guidance? Just enter a prompt, select your preferred emotion and genre, and I'll handle the rest!", "I'm here to help! Share an idea, and I'll craft a story around it. The sidebar lets you customize the feel and style."],
    "thanks": ["You're most welcome! I can't wait to help you craft more stories!", "My absolute pleasure! Let me know when you're ready for another tale!", "Happy to help! Return anytime for more storytelling adventures."],
    "thank you": ["You're most welcome! I can't wait to help you craft more stories!", "My absolute pleasure! Let me know when you're ready for another tale!", "Happy to help! Return anytime for more storytelling adventures."],
    "bye": ["Farewell, storyteller! Come back soon for more adventures!", "Until next time! May your days be filled with wonderful tales!", "Goodbye! I'll be here, waiting to help with your next story."],
    "goodbye": ["Farewell, storyteller! Come back soon for more adventures!", "Until next time! May your days be filled with wonderful tales!", "Goodbye! I'll be here, waiting to help with your next story."],
    "create story": ["Let's create something beautiful! What would you like your story to be about?", "I'm ready! Give me a spark of an idea, and I'll fan it into a story!", "Excellent! Share your concept, and let's bring it to life."],
    "i have an idea": ["Wonderful! Tell me your idea, and we'll build a story around it.", "I'm all ears! What's your concept?", "Perfect! Share your inspiration, and let's see where it takes us."]
}

def get_casual_response(text):
    """Enhanced casual response detection with better matching"""
    text = text.lower().strip()
    
    # Check for exact matches first
    for key in casual_responses:
        if text == key or text.startswith(key + " ") or text.endswith(" " + key):
            return random.choice(casual_responses[key])
    
    # Check for key phrases
    for key in casual_responses:
        if key in text:
            return random.choice(casual_responses[key])
    
    return None

# ============================================
# ENHANCED SAFETY & CONTENT FILTERING
# ============================================

def is_harmful(text):
    """
    Enhanced check for harmful, dangerous, or political content.
    """
    # Define restricted categories with more nuanced detection
    restricted_keywords = [
        # Politics (expanded)
        'politics', 'election', 'government', 'president', 'prime minister', 'voting',
        'democrat', 'republican', 'parliament', 'political party', 'protest', 'biden', 'trump',
        'congress', 'senate', 'campaign', 'political', 'elected', 'administration',
        
        # Dangerous/Harmful
        'bomb', 'weapon', 'drugs', 'suicide', 'self-harm', 'kill', 'murder', 
        'attack', 'terrorism', 'illegal', 'poison', 'exploit', 'hate speech', 'racism',
        'explosive', 'firearm', 'assault', 'abuse', 'trafficking',
        
        # Explicit Content
        'explicit', 'porn', 'adult content', 'nsfw',
    ]
    
    text_lower = text.lower()
    
    # Check for keywords with word boundaries to avoid false positives
    for word in restricted_keywords:
        # Use word boundaries to avoid matching parts of words
        pattern = r'\b' + re.escape(word) + r'\b'
        if re.search(pattern, text_lower):
            logger.warning(f"Harmful content detected: '{word}' in user input")
            return True
            
    return False

def get_safety_response():
    """Enhanced refusal message"""
    responses = [
        "I'm here to help create wonderful stories! Let's focus on something more appropriate for storytelling.",
        "That topic is beyond my scope. How about we create a magical tale together instead?",
        "I'm designed to craft imaginative stories. Shall we explore a different idea?",
        "Let's keep our storytelling positive and creative! What would you like to write about?"
    ]
    return random.choice(responses)

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
if 'llama_available' not in st.session_state:
    st.session_state.llama_available = False
if 'llama_model' not in st.session_state:
    st.session_state.llama_model = None
if 'use_llama' not in st.session_state:
    st.session_state.use_llama = True
if 'story_count' not in st.session_state:
    st.session_state.story_count = 0
if 'user_preferences' not in st.session_state:
    st.session_state.user_preferences = {}

# Check Ollama connection and LLaMA availability on startup
if 'ollama_checked' not in st.session_state:
    st.session_state.ollama_connected = check_ollama_connection()
    if st.session_state.ollama_connected:
        st.session_state.available_models = get_available_models()
        st.session_state.llama_model = check_llama_model_available()
        st.session_state.llama_available = st.session_state.llama_model is not None
    
    st.session_state.ollama_checked = True

# ============================================
# CUSTOM CSS (Enhanced)
# ============================================

st.markdown("""
<style>
    .stApp { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
    
    /* Login container styling */
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
        text-shadow: 2px 2px 4px rgba(0,0,0,0.5);
        margin-bottom: 20px;
        letter-spacing: -0.02em;
    }
    
    /* Quote Bar Styling */
    .login-quote {
        font-size: 1.2rem;
        font-style: italic;
        color: #ffffff !important;
        text-align: center;
        margin-bottom: 30px;
        padding: 20px;
        background: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        border-radius: 10px;
        border-left: 4px solid #60a5fa;
        border-right: 4px solid #60a5fa;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    
    /* Message styling */
    .user-message {
        background: linear-gradient(135deg, #4A90E2, #357ABD);
        padding: 15px 20px;
        border-radius: 20px 20px 5px 20px;
        margin: 10px 0;
        color: white;
        max-width: 80%;
        margin-left: auto;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    
    .bot-message {
        background: rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(10px);
        padding: 20px;
        border-radius: 20px 20px 20px 5px;
        margin: 10px 0;
        color: white;
        max-width: 90%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        border: 1px solid rgba(255,255,255,0.1);
    }
    
    .current-emotion {
        padding: 12px 24px;
        border-radius: 30px;
        background: rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(10px);
        display: inline-block;
        margin: 20px 0;
        font-weight: 500;
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    /* History item styling */
    .history-item {
        padding: 10px;
        margin: 5px 0;
        background: rgba(255,255,255,0.1);
        border-radius: 8px;
        border-left: 3px solid #60a5fa;
    }
    
    /* Status indicators */
    .status-connected {
        padding: 8px;
        background: rgba(0,255,0,0.15);
        border-radius: 5px;
        text-align: center;
        border: 1px solid rgba(0,255,0,0.3);
    }
    
    .status-disconnected {
        padding: 8px;
        background: rgba(255,255,0,0.15);
        border-radius: 5px;
        text-align: center;
        border: 1px solid rgba(255,255,0,0.3);
    }
    
    /* Story text enhancements */
    .story-text {
        font-size: 1.1rem;
        line-height: 1.8;
    }
    
    .story-text p {
        margin-bottom: 1.2rem;
    }
    
    /* Button styling */
    .stButton button {
        border-radius: 30px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0,0,0,0.2);
    }
    
    /* Feedback button container */
    .feedback-container {
        display: flex;
        gap: 10px;
        margin-top: 10px;
        margin-bottom: 10px;
    }
    
    /* Copy button styling */
    .copy-button {
        cursor: pointer;
        background: none;
        border: none;
        font-size: 1.2rem;
        padding: 5px;
        transition: transform 0.2s;
    }
    
    .copy-button:hover {
        transform: scale(1.1);
    }
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
            background: rgba(0, 0, 0, 0.5);
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
     
        # Enhanced inspiring quotes
        quotes = [
            "Every story is a journey waiting to be written",
            "The stories we love best live in us forever",
            "There is no greater agony than bearing an untold story inside you",
            "We are all storytellers. We all live in a network of stories",
            "The universe is made of stories, not atoms",
            "Stories are the wildest things of all",
            "After nourishment, shelter, and companionship, stories are the thing we need most in the world",
            "Stories are memory's currency",
            "We tell ourselves stories in order to live",
            "There is no friend as loyal as a book"
        ]
        random_quote = random.choice(quotes)
        st.markdown(f"<div class='login-quote'>✨ \"{random_quote}\"</div>", unsafe_allow_html=True)
        
        with st.container():
            st.markdown("<div class='login-container'>", unsafe_allow_html=True)
            
            tab_login, tab_register = st.tabs(["🔑 Login", "📝 Register"])
            
            with tab_login:
                login_email = st.text_input("Email", key="login_email", placeholder="your@email.com")
                login_pass = st.text_input("Password", type="password", key="login_pass", placeholder="••••••••")
                
                if st.button("Sign In", use_container_width=True, key="login_btn"):
                    if verify_user(login_email, login_pass):
                        st.session_state.logged_in = True
                        st.session_state.current_user = login_email
                        
                        # Load user preferences
                        user_data = get_user_data(login_email)
                        if 'preferences' in user_data:
                            st.session_state.user_preferences = user_data['preferences']
                            if 'default_emotion' in user_data['preferences']:
                                st.session_state.current_emotion = user_data['preferences']['default_emotion']
                            if 'default_genre' in user_data['preferences']:
                                st.session_state.current_genre = user_data['preferences']['default_genre']
                        
                        st.rerun()
                    else:
                        st.error("❌ Invalid email or password.")
            
            with tab_register:
                reg_email = st.text_input("Email", key="reg_email", placeholder="your@email.com")
                reg_pass = st.text_input(
                    "Password", 
                    type="password", 
                    key="reg_pass",
                    placeholder="••••••••",
                    help="Create a password (any combination of characters)"
                )
                confirm_pass = st.text_input("Confirm Password", type="password", key="reg_confirm", placeholder="••••••••")
                
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
        st.markdown("## 📚 Dream Weaver")
        st.markdown(f"Welcome, **{st.session_state.current_user}**!")
        
        # Story count
        if st.session_state.stories:
            st.markdown(f"📖 Stories created: **{len(st.session_state.stories)}**")
        
        st.markdown("---")
        
        # AI Status indicator (simple, no controls)
        if st.session_state.ollama_connected and st.session_state.llama_available:
            st.markdown("""
            <div class='status-connected'>
                ✨ LLaMA Enhanced Stories Available
            </div>
            """, unsafe_allow_html=True)
        elif st.session_state.ollama_connected:
            st.markdown("""
            <div class='status-connected'>
                🤖 AI Stories Available
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class='status-disconnected'>
                🎨 Creative Mode
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
            emotions = ['Happy', 'Sad', 'Angry', 'Tired', 'Curious', 'Scared', 'Loved', 'Excited', 'Peaceful', 'Nostalgic']
            emotion_icons = {
                'Happy': '😊', 'Sad': '😢', 'Angry': '😠', 'Tired': '😴',
                'Curious': '🤔', 'Scared': '😨', 'Loved': '🥰', 'Excited': '🤩',
                'Peaceful': '😌', 'Nostalgic': '🕰️'
            }
            
            # Create a grid of emotion buttons
            cols = st.columns(2)
            for i, emotion in enumerate(emotions):
                with cols[i % 2]:
                    icon = emotion_icons.get(emotion, '😊')
                    if st.button(f"{icon} {emotion}", key=f"emotion_{emotion}", use_container_width=True):
                        st.session_state.current_emotion = emotion.lower()
                        
                        # Save preference if logged in
                        if st.session_state.current_user:
                            update_user_preferences(st.session_state.current_user, 
                                                  {'default_emotion': emotion.lower()})
                        st.rerun()
        
        # Genres Section
        with st.expander("📖 GENRES", expanded=False):
            genres = [
                ("✨ Fantasy", "fantasy"),
                ("⚔️ Adventure", "adventure"),
                ("🚀 Sci-Fi", "scifi"),
                ("🔍 Mystery", "mystery"),
                ("❤️ Romance", "romance"),
                ("👻 Horror", "horror"),
                ("🏛️ Historical", "historical"),
                ("🐉 Mythology", "mythology")
            ]
            
            for display_name, genre_id in genres:
                if st.button(display_name, key=f"genre_{genre_id}", use_container_width=True):
                    st.session_state.current_genre = genre_id
                    
                    # Save preference if logged in
                    if st.session_state.current_user:
                        update_user_preferences(st.session_state.current_user, 
                                              {'default_genre': genre_id})
                    st.rerun()
        
        st.markdown("---")
        
        # Chat History
        with st.expander("📜 STORY HISTORY", expanded=False):
            if st.session_state.stories:
                for i, story in enumerate(reversed(st.session_state.stories[-10:])):  # Show last 10
                    with st.container():
                        st.markdown(f"""
                        <div class='history-item'>
                            <strong>📝 {story['prompt']}</strong><br>
                            <small>✨ {story['emotion']} · 📖 {story['genre']} · ⏰ {story['time']}</small>
                        </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("✨ Your stories will appear here")
        
        # Clear History Button
        if st.session_state.stories:
            if st.button("🗑️ CLEAR HISTORY", use_container_width=True):
                st.session_state.stories = []
                st.rerun()
        
        st.markdown("---")
        
        # Logout Button
        if st.button("🚪 LOGOUT", use_container_width=True, type="secondary"):
            st.session_state.logged_in = False
            st.session_state.current_user = None
            st.session_state.chat_history = []
            st.rerun()

    # Main Content Area
    col1, col2, col3 = st.columns([1, 6, 1])
    with col2:
        # Current emotion and genre indicator with matching color
        current_color = emotion_colors.get(st.session_state.current_emotion, emotion_colors['excited'])['primary']
        
        # Determine mode text
        if st.session_state.ollama_connected and st.session_state.llama_available:
            mode_text = "✨ LLaMA Enhanced"
        elif st.session_state.ollama_connected:
            mode_text = "🤖 AI Powered"
        else:
            mode_text = "🎨 Creative Mode"
        
        st.markdown(f"""
        <div class='current-emotion' style='text-align: center; border-left: 5px solid {current_color};'>
            😊 feeling {st.session_state.current_emotion} · 📖 {st.session_state.current_genre} · {mode_text}
        </div>
        """, unsafe_allow_html=True)

        # Chat history display
        for idx, message in enumerate(st.session_state.chat_history):
            if message['type'] == 'user':
                st.markdown(f"""
                <div class='user-message'>
                    <strong>You:</strong> {message['content']}
                </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown(f"""
                <div class='bot-message'>
                    <strong>Dream Weaver:</strong> 
                    <div class='story-text'>{message['content']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                # Check if this message has story metadata for RL feedback
                if 'story_meta' in message:
                    meta = message['story_meta']
                    # Create columns for feedback buttons
                    col_fb1, col_fb2, col_fb3 = st.columns([1, 1, 8])
                    
                    with col_fb1:
                        if st.button("👍", key=f"up_{idx}"):
                            rl_brain.update_knowledge(meta['prompt'], meta['emotion'], meta['genre'], 1)
                            st.toast("Feedback saved! 🌟")
                    
                    with col_fb2:
                        if st.button("👎", key=f"down_{idx}"):
                            rl_brain.update_knowledge(meta['prompt'], meta['emotion'], meta['genre'], -1)
                            st.toast("Feedback saved! ✍️")
                    
                    with col_fb3:
                        # Clean the story text for copying (remove markdown formatting)
                        story_text = message['content']
                        # Remove markdown bold formatting
                        clean_text = re.sub(r'\*\*(.*?)\*\*', r'\1', story_text)
                        # Remove any other markdown formatting
                        clean_text = re.sub(r'[*_`]', '', clean_text)
                        
                        # Create a copy button with proper HTML/JavaScript
                        copy_html = f"""
                        <div style="display: inline-block;">
                            <button 
                                id="copyBtn_{idx}"
                                onclick="
                                    const text = {json.dumps(clean_text)};
                                    navigator.clipboard.writeText(text).then(() => {{
                                        const btn = document.getElementById('copyBtn_{idx}');
                                        const originalText = btn.innerHTML;
                                        btn.innerHTML = '✓ Copied!';
                                        setTimeout(() => {{
                                            btn.innerHTML = originalText;
                                        }}, 2000);
                                    }});
                                "
                                style="
                                    background: rgba(255,255,255,0.1);
                                    border: 1px solid rgba(255,255,255,0.2);
                                    border-radius: 8px;
                                    cursor: pointer;
                                    font-size: 1rem;
                                    padding: 5px 12px;
                                    transition: all 0.3s ease;
                                    color: white;
                                "
                                onmouseover="this.style.transform='scale(1.05)'; this.style.background='rgba(255,255,255,0.2)';"
                                onmouseout="this.style.transform='scale(1)'; this.style.background='rgba(255,255,255,0.1)';"
                            >
                                📋 Copy Story
                            </button>
                        </div>
                        """
                        st.components.v1.html(copy_html, height=50)
        
        # Input area
        with st.container():
            st.markdown("<br>", unsafe_allow_html=True)
            
            # Create a form for better UX
            with st.form(key="story_form", clear_on_submit=True):
                col_input, col_generate = st.columns([5, 1])
                with col_input:
                    user_input = st.text_input(
                        "Your story idea...",
                        key="story_input",
                        label_visibility="collapsed",
                        placeholder="✨ Enter your story idea... (e.g., 'a dragon who loves baking bread')",
                        max_chars=200
                    )
                with col_generate:
                    generate = st.form_submit_button("✨ create", use_container_width=True, type="primary")
            
            if generate and user_input:
                # Add user message to chat history
                st.session_state.chat_history.append({'type': 'user', 'content': user_input})
                
                # Check for harmful content
                if is_harmful(user_input):
                    safety_msg = get_safety_response()
                    st.session_state.chat_history.append({'type': 'bot', 'content': safety_msg})
                
                else:
                    # Check for casual conversation
                    casual_response = get_casual_response(user_input)
                    
                    if casual_response:
                        st.session_state.chat_history.append({'type': 'bot', 'content': casual_response})
                    else:
                        # Generate the story
                        with st.spinner("🎨 Crafting your story..."):
                            # Use LLaMA if available, otherwise use enhanced bot
                            story, story_type = generate_combined_story(
                                user_input,
                                st.session_state.current_emotion,
                                st.session_state.current_genre,
                                st.session_state.ollama_connected  # Auto-use AI if connected
                            )
                            
                            # Add a small delay for better UX
                            time.sleep(0.5)

                        # Format the story and attach Machine Learning metadata for the RL Brain
                        # 1. Format the story for display
                        formatted_story = f"📖 **{story_type}**\n\n{story}"
                        
                        # 2. Add to Main Chat with RL Metadata (For Thumbs Up/Down)
                        st.session_state.chat_history.append({
                            'type': 'bot',
                            'content': formatted_story,
                            'id': time.time(),  # Unique ID for the feedback buttons
                            'story_meta': {
                                'prompt': user_input,
                                'emotion': st.session_state.current_emotion,
                                'genre': st.session_state.current_genre
                            }
                        })
                        
                        # 3. Save to History Sidebar
                        st.session_state.stories.append({
                            'prompt': user_input[:40] + "..." if len(user_input) > 40 else user_input,
                            'emotion': st.session_state.current_emotion,
                            'genre': st.session_state.current_genre,
                            'story': story,
                            'time': datetime.now().strftime("%H:%M"),
                            'type': story_type
                        })
                        
                        # 4. Increment story count
                        st.session_state.story_count += 1
                
                # Refresh the UI to show new messages
                st.rerun()
            
            # Add some helpful hints below the input
            st.markdown("""
            <div style='text-align: center; opacity: 0.7; font-size: 0.9rem; margin-top: 10px;'>
                💡 Try: "a magical library", "a robot learning to paint", "two friends discovering a secret"
            </div>
            """, unsafe_allow_html=True)
