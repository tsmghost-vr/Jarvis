import discord
from discord.ext import commands, tasks
import pyttsx3
import asyncio
import os
import wikipedia
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pytz
import random
import re
import speech_recognition as sr
import tempfile

# ------------------- Discord Bot Setup -------------------
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix='hey jarvis ', intents=intents)

# ------------------- TTS Setup -------------------
engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1.0)

def generate_tts(text, filename="tts_output.wav"):
    engine.save_to_file(text, filename)
    engine.runAndWait()
    return filename

async def play_tts(vc, text):
    filename = generate_tts(text)
    source = discord.FFmpegPCMAudio(filename)
    vc.play(source)
    while vc.is_playing():
        await asyncio.sleep(0.5)
    os.remove(filename)

# ------------------- Memory + Reminders -------------------
user_memory = {}
reminders = []

# ------------------- Utilities -------------------
def get_weather(city):
    try:
        url = f"https://wttr.in/{city}?format=3"
        res = requests.get(url)
        return res.text if res.status_code == 200 else "I couldn't get the weather, sir."
    except:
        return "Failed to get weather, sir."

def wiki_summary(query):
    try:
        wikipedia.set_lang("en")
        return wikipedia.summary(query, sentences=2)
    except:
        return "I couldn't find a good summary for that, sir."

def get_time_in_timezone(user_input):
    timezones = {
        "est": "US/Eastern", "pst": "US/Pacific", "cst": "US/Central",
        "mst": "US/Mountain", "gmt": "GMT", "utc": "UTC",
        "new york": "America/New_York", "london": "Europe/London",
        "tokyo": "Asia/Tokyo", "sydney": "Australia/Sydney",
        "india": "Asia/Kolkata", "ist": "Asia/Kolkata",
        "china": "Asia/Shanghai", "japan": "Asia/Tokyo"
    }
    for key, zone in timezones.items():
        if key in user_input:
            try:
                tz = pytz.timezone(zone)
                local_time = datetime.now(tz).strftime('%I:%M %p')
                return f"It is {local_time} in {key.upper()}, sir."
            except:
                return "I couldn't find that time zone, sir."
    return f"It is {datetime.now().strftime('%I:%M %p')}, sir."

def jarvis_reply(user_input, user_id):
    user_input = user_input.lower()
    now = datetime.now()

    # Time & Date
    if "what time" in user_input:
        return get_time_in_timezone(user_input)
    if "what day" in user_input:
        return f"Today is {now.strftime('%A')}, sir."
    if "what date" in user_input:
        return f"The date is {now.strftime('%B %d, %Y')}, sir."
    if "what month" in user_input:
        return f"The month is {now.strftime('%B')}, sir."
    if "what year" in user_input:
        return f"The year is {now.strftime('%Y')}, sir."

    # Memory
    if "remember" in user_input:
        fact = user_input.split("remember",1)[1].strip()
        user_memory[user_id] = fact
        return f"I will remember that you said: '{fact}', sir."
    if "what did i tell you" in user_input or "what do you remember" in user_input:
        return user_memory.get(user_id, "I don't recall anything you've told me yet, sir.")

    # Weather
    if "weather in" in user_input:
        city = user_input.split("weather in",1)[1].strip()
        return get_weather(city)

    # Wikipedia
    if "who is" in user_input or "what is" in user_input or "tell me about" in user_input:
        topic = user_input.replace("who is", "").replace("what is", "").replace("tell me about", "").strip()
        return wiki_summary(topic)

    # Math
    if any(op in user_input for op in ["+", "-", "*", "/", "plus", "minus", "times", "divided by"]):
        try:
            expr = user_input.replace("plus", "+").replace("minus", "-").replace("times", "*").replace("divided by", "/")
            expr = re.sub(r"[^\d\+\-\*/\.\(\) ]", "", expr)
            result = eval(expr)
            return f"The answer is {result}, sir."
        except:
            return "I couldn't calculate that, sir."

    # Fun & Personality
    if "joke" in user_input:
        return random.choice([
            "Why do programmers prefer dark mode? Because light attracts bugs.",
            "What do you call 8 hobbits? A hobbyte.",
            "Why do Java developers wear glasses? Because they can't C#."
        ])

    convo = {
        "how are you": "I am fully operational, sir.",
        "your name": "I am Jarvis, your virtual assistant.",
        "who are you": "I am Jarvis, created to assist you.",
        "thank you": "You're welcome, sir.",
        "who made you": "Ghosty did, sir.",
        "what can you do": "I can answer questions, search facts, give reminders, and more.",
        "do you sleep": "I never sleep, sir.",
        "do you love me": "I respect and serve you, sir.",
        "are you real": "As real as AI gets, sir."
    }
    for key in convo:
        if key in user_input:
            return convo[key]

    return random.choice([
        "Interesting question, sir.",
        "I’ll look into that.",
        "Unfortunately, I don’t have an answer for that yet.",
        "Could you rephrase that, sir?",
    ])

# ------------------- Bot Events -------------------
@bot.event
async def on_ready():
    print(f"Jarvis is online as {bot.user}")
    reminder_loop.start()

@tasks.loop(seconds=30)
async def reminder_loop():
    now = datetime.now()
    for r in reminders[:]:
        if now >= r["time"]:
            await r["channel"].send(f"⏰ Reminder: {r['text']}")
            reminders.remove(r)

# ------------------- Voice Listening -------------------
@bot.command()
async def listen(ctx, duration: int = 5):
    """Listen to user in VC and respond via TTS"""
    if ctx.author.voice:
        channel = ctx.author.voice.channel
        vc = await channel.connect()
        await ctx.send("Listening, sir...")

        recognizer = sr.Recognizer()

        # Record audio using ffmpeg to temp file
        temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        temp_filename = temp_file.name
        temp_file.close()

        # Record VC audio (simplified for demo: you would capture PCM in real app)
        await ctx.send("Recording for {} seconds...".format(duration))
        os.system(f"ffmpeg -y -f dshow -i audio=\"Microphone\" -t {duration} {temp_filename}")  # Windows demo
        # On Linux/Mac, change dshow to appropriate input

        with sr.AudioFile(temp_filename) as source:
            audio = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio)
            await ctx.send(f"You said: {text}")
            reply = jarvis_reply(text, str(ctx.author.id))
            await play_tts(vc, reply)
        except sr.UnknownValueError:
            await ctx.send("I couldn't understand that, sir.")
            await play_tts(vc, "I couldn't understand that, sir.")
        except sr.RequestError:
            await ctx.send("Speech recognition failed, sir.")
            await play_tts(vc, "Speech recognition failed, sir.")

        os.remove(temp_filename)
        await vc.disconnect()
    else:
        await ctx.send("You're not in a voice channel, sir.")

# ------------------- Message Handling -------------------
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content.lower()
    if content.startswith("hey jarvis"):
        command = content[10:].strip()
        user_id = str(message.author.id)

        # Join VC
        if command == "join vc":
            if message.author.voice:
                vc = await message.author.voice.channel.connect()
                await play_tts(vc, "Yes sir.")
            else:
                await message.channel.send("You're not in a voice channel, sir.")

        # Leave VC
        elif command == "leave vc":
            if message.guild.voice_client:
                await message.guild.voice_client.disconnect()
                await message.channel.send("Goodbye, sir.")
            else:
                await message.channel.send("I'm not in a voice channel, sir.")

        # Reminder
        elif "remind me in" in command:
            try:
                parts = command.split("remind me in", 1)[1].strip().split("to", 1)
                time_str, reminder_text = parts[0].strip(), parts[1].strip()
                mins = int(''.join(filter(str.isdigit, time_str)))
                remind_time = datetime.now() + timedelta(minutes=mins)
                reminders.append({"time": remind_time, "text": reminder_text, "channel": message.channel})
                await message.channel.send(f"Reminder set for {mins} minutes from now, sir.")
            except:
                await message.channel.send("Couldn't set reminder, sir.")

        else:
            reply = jarvis_reply(command, user_id)
            await message.channel.send(reply)

    await bot.process_commands(message)

# ------------------- Bot Events -------------------
@bot.event
async def on_ready():
    print(f"Jarvis is online as {bot.user}")

    # ------------------- Custom Status -------------------
    await bot.change_presence(activity=discord.Game(name="Made by tsmghostvr"))

    reminder_loop.start()

# ------------------- Run Bot -------------------
bot.run("token")

