import discord
import aiohttp
import os 
from dotenv import load_dotenv

load_dotenv()
DISCORD_BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENROUTER_API_URL = 'https://openrouter.ai/api/v1/chat/completions'
OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')  # Add this to your .env file

# Popular models on OpenRouter
AVAILABLE_MODELS = {
    "deepseek-r1-qwen14b": "deepseek/deepseek-r1-distill-qwen-14b:free",
    "deepseek-r1-qwen32b": "deepseek/deepseek-r1-distill-qwen-32b:free",
    "deepseek-r1":"deepseek/deepseek-r1-0528:free",
    "deepseek-v3":"deepseek/deepseek-chat-v3-0324:free",
}
# deepseek/deepseek-r1-0528:free deepseek/deepseek-r1:free tngtech/deepseek-r1t-chimera:free deepseek/deepseek-chat:free
# deepseek/deepseek-r1-0528-qwen3-8b:free deepseek/deepseek-r1-distill-llama-70b:free deepseek/deepseek-prover-v2:free
DEFAULT_MODEL = "deepseek-v3"

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

# Store session per user_id: model and message history
user_sessions = {}

@client.event
async def on_ready():
    print(f'Bot online as {client.user}')

def create_model_embed():
    embed = discord.Embed(
        title="Available Models",
        description="Choose a model by typing `!model model_name`",
        color=discord.Color.blue()
    )
    
    for model_id, model_name in AVAILABLE_MODELS.items():
        embed.add_field(name=model_id, value=model_name, inline=False)
    
    embed.set_footer(text=f"Current default model: {DEFAULT_MODEL}")
    return embed

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

        # Command to list available models
        if content == "!models":
            await message.channel.send(embed=create_model_embed())
            return

        # Command to change model
        if content.startswith("!model"):
            parts = content.split()
            if len(parts) >= 2:
                new_model = parts[1]
                if new_model in AVAILABLE_MODELS:
                    session["model"] = new_model
                    session["history"] = []  # Clear history when changing models
                    await message.channel.send(f"Model switched to `{new_model}` ({AVAILABLE_MODELS[new_model]}). Conversation history cleared.")
                else:
                    await message.channel.send(f"Invalid model. Use `!models` to see available options.")
            else:
                await message.channel.send("Usage: `!model model_name`\nUse `!models` to see available options.")
            return

        # Command to clear conversation history
        if content == "!clear":
            session["history"] = []
            await message.channel.send("Conversation history cleared.")
            return

        # Command to show current model
        if content == "!current":
            model_name = AVAILABLE_MODELS.get(session["model"], session["model"])
            await message.channel.send(f"Current model: `{session['model']}` ({model_name})")
            return

        # Append user message to history
        session["history"].append({"role": "user", "content": content})

        # Prepare payload for OpenRouter API
        payload = {
            "model": session["model"],
            "messages": session["history"],
        }

        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "HTTP-Referer": "https://your-site-url.com",  # Optional but recommended
            "X-Title": "Discord AI Bot"  # Optional but recommended
        }

        await message.channel.typing()

        try:
            async with aiohttp.ClientSession() as http_session:
                async with http_session.post(
                    OPENROUTER_API_URL,
                    json=payload,
                    headers=headers
                ) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        reply = data["choices"][0]["message"]["content"]
                    else:
                        error_data = await resp.json()
                        error_msg = error_data.get("error", {}).get("message", f"API error with status code {resp.status}")
                        reply = f"OpenRouter API error: {error_msg}"
        except Exception as e:
            reply = f"Error contacting OpenRouter API: {str(e)}"

        # Append assistant reply to history
        session["history"].append({"role": "assistant", "content": reply})

        # Split long messages to avoid Discord's character limit
        if len(reply) > 2000:
            for chunk in [reply[i:i+2000] for i in range(0, len(reply), 2000)]:
                await message.channel.send(chunk)
        else:
            await message.channel.send(reply)

client.run(DISCORD_BOT_TOKEN)
