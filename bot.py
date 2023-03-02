import os
from dotenv import load_dotenv
import openai
from functools import wraps
import tempfile
from telegram import Update, Audio
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters
import pydub
from pydub import AudioSegment
import logging

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

allowed_user_ids_str = os.getenv("ALLOWED_USER_IDS")
allowed_user_ids = allowed_user_ids_str.split(",") if allowed_user_ids_str else []

def restricted(func):
    @wraps(func)
    async def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id.__str__()
        if allowed_user_ids and user_id not in allowed_user_ids:
            print(f"Unauthorized access denied for {user_id}.")
            return

        return await func(update, context, *args, **kwargs)
    return wrapped

def answer_question(question, context):
    blank_chat_history = [
      {"role": "system", "content": "You are a helpful assistant."}
    ]

    # retrieve chat history, if there is none, use the blank chat history
    chat_history = context.chat_data.get('history', blank_chat_history)

    # append user input to chat history
    chat_history.append({"role": "user", "content": question})

    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=chat_history,
    )

    # append response to chat history
    chat_history.append({ "role": "assistant", "content": response.choices[0].message.content })

    # update chat history
    context.chat_data['history'] = chat_history

    return response.choices[0].message.content

    
@restricted
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text
    await update.message.reply_text(answer_question(user_input, context))


@restricted
async def transcribe_audio(update: Update, context) -> None:
    audio_file = await update.message.voice.get_file()
    with tempfile.NamedTemporaryFile(suffix=".mp3") as f:
        await audio_file.download_to_drive(f.name)
        sound = AudioSegment.from_ogg(f.name)
        sound.export(f.name, format="mp3")
        transcript = openai.Audio.transcribe("whisper-1", f)
        await update.message.reply_text(transcript["text"]) 

    await update.message.reply_text(answer_question(transcript["text"], context))

@restricted
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['history'] = []
    await update.message.reply_text('Chat history cleared.')

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello, I am a chatbot. Ask me a question. You can also send me an audio message and I will answer it.')

async def post_init(application) -> None:
    await application.bot.set_my_commands(
            [('start', 'Starts the bot'), ('clear', 'Clears the chat history')]
        )

app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_API_TOKEN")).post_init(post_init).build()

app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))
app.add_handler(MessageHandler(filters.VOICE, transcribe_audio))

app.run_polling()
