import discord
import aiohttp
import os 
DISCORD_BOT_TOKEN = os.getenv('BOT_TOKEN')
OLLAMA_URL = 'http://localhost:5000/api/chat'
DEFAULT_MODEL = 'dolphin3:latest'  # change if you want

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Store session per user_id: model and message history
user_sessions = {}

@client.event
async def on_ready():
    print(f'Bot online as {client.user}')

@client.event
async def on_message(message):
    # Ignore messages from the bot itself
    if message.author == client.user:
        return

    # Only respond to DMs
    if isinstance(message.channel, discord.DMChannel):
        user_id = str(message.author.id)
        content = message.content.strip()

        # Initialize user session if not exist
        if user_id not in user_sessions:
            user_sessions[user_id] = {
                "model": DEFAULT_MODEL,
                "history": []
            }

        session = user_sessions[user_id]

        # Command to fix/change model
        if content.startswith("!model_fix"):
            parts = content.split()
            if len(parts) >= 2:
                new_model = parts[1]
                session["model"] = new_model
                session["history"] = []
                await message.channel.send(f"Model switched to `{new_model}` and conversation history cleared.")
            else:
                await message.channel.send("Usage: `!model_fix model_name`")
            return

        # Append user message to history
        session["history"].append({"role": "user", "content": content})

        # Prepare payload for Ollama API
        payload = {
            "model": session["model"],
            "messages": session["history"],
            "stream": False  # Set True if your API supports streaming and you want partial responses
        }

        await message.channel.typing()

        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(OLLAMA_URL, json=payload) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        # The exact key depends on Ollama's API response format
                        reply = data.get("message", {}).get("content", None)
                        if not reply:
                            reply = "Ollama API returned no reply."
                    else:
                        reply = f"Ollama API error with status code {resp.status}"
        except Exception as e:
            reply = f"Error contacting Ollama API: {str(e)}"

        # Append assistant reply to history
        session["history"].append({"role": "assistant", "content": reply})

        await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
