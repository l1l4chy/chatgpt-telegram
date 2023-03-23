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
from telegram.constants import ChatAction

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

allowed_user_ids_str = os.getenv("ALLOWED_USER_IDS")
allowed_user_ids = allowed_user_ids_str.split(",") if allowed_user_ids_str else []

BLANK_CHAT_HISTORY = [
    {"role": "system", "content": "You are a helpful assistant."}
]
DEFAULT_MODEL = "gpt-3.5-turbo"
PRICING = {
    "gpt-4-0314": {
        "prompt_tokens": 0.00003,
        "completion_tokens": 0.00006
    },
    "gpt-3.5-turbo": {
        "tokens": 0.000002
    }
}

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
    # retrieve chat history, if there is none, use the blank chat history
    chat_history = context.chat_data.get('history', BLANK_CHAT_HISTORY)

    # append user input to chat history
    chat_history.append({"role": "user", "content": question})

    selected_model = context.chat_data.get('model', DEFAULT_MODEL)

    response = openai.ChatCompletion.create(
      model=selected_model,
      messages=chat_history,
      max_tokens=2000,
    )

    # append response to chat history
    chat_history.append({ "role": "assistant", "content": response.choices[0].message.content })

    # update chat history
    context.chat_data['history'] = chat_history

    content = response.choices[0].message.content

    message_cost = calculate_message_cost(response, selected_model, context.chat_data.get('total_cost', 0))
    total_cost = context.chat_data.get('total_cost', 0) + message_cost
    context.chat_data['total_cost'] = total_cost

    if context.chat_data.get('show_cost', False):
        # append selected model, message cost and total cost
        content += f"\n\n(model: {selected_model}, message cost: ${message_cost}, total cost: ${total_cost})"

    return content

def calculate_message_cost(response, selected_model=DEFAULT_MODEL, total_cost=0):
    global PRICING

    message_cost = 0
    if selected_model == "gpt-4-0314":
        message_cost = PRICING[selected_model]["prompt_tokens"] * response.usage.prompt_tokens + PRICING[selected_model]["completion_tokens"] * response.usage.completion_tokens
    elif selected_model == "gpt-3.5-turbo":
        message_cost = PRICING[selected_model]["tokens"] * response.usage.total_tokens

    # print prompt tokens count and completion tokens count
    print(f"Prompt tokens: {response.usage.prompt_tokens}, completion tokens: {response.usage.completion_tokens}")
    # print message cost and total cost in dollars
    print(f"Message cost: ${message_cost}, total cost: ${total_cost + message_cost} (model: {selected_model})")

    return message_cost

user_inputs = {}

async def process_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.chat_id
    print(f"Processing message from {chat_id}")
    aggregated_message = " ".join(user_inputs[chat_id])
    del user_inputs[chat_id]

    answer = answer_question(aggregated_message, context)
    if len(answer) > 4096:
        parts_count = len(answer) // 4096
        for i in range(0, len(answer), 4096):
            print(f"Answering to {chat_id} by parts. Part {i}/{parts_count}")
            await context.bot.sent_message(chat_id=chat_id, text=answer[i:i+4096])
    else:
        print(f"Answering to {chat_id}")
        await context.bot.send_message(chat_id=chat_id, text=answer)

def remove_job_if_exists(name: str, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

@restricted
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    user_input = update.message.text

    if user_id not in user_inputs:
        user_inputs[user_id] = []  # Initialize user input list for this user

    print("Appending message to user input list")
    user_inputs[user_id].append(user_input)  # Append current message to user input list

    job_removed = remove_job_if_exists(str(user_id), context)  # Remove job if exists
    context.job_queue.run_once(process_message, 2, chat_id=update.message.chat_id, name=str(user_id))


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
    global user_inputs
    user_id = update.effective_user.id
    if user_id in user_inputs:
        del user_inputs[user_id]
    context.chat_data['history'] = []
    await update.message.reply_text('Chat history cleared.')

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello, I am a chatbot. Ask me a question. You can also send me an audio message and I will answer it.')

@restricted
async def use_gpt3(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['model'] = "gpt-3.5-turbo"
    await update.message.reply_text('Using GPT-3')

@restricted
async def use_gpt4(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['model'] = "gpt-4-0314"
    await update.message.reply_text('Using GPT-4')

@restricted
async def show_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['show_cost'] = True
    await update.message.reply_text('Showing cost')

@restricted
async def hide_cost(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['show_cost'] = False
    await update.message.reply_text('Hiding cost')

async def post_init(application) -> None:
    await application.bot.set_my_commands(
            [
                ('start', 'Starts the bot'),
                ('clear', 'Clears the chat history'),
                ('use_gpt3', 'Use GPT-3'),
                ('use_gpt4', 'Use GPT-4'), 
                ('show_cost', 'Show cost'), 
                ('hide_cost', 'Hide cost')
            ]
        )

app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_API_TOKEN")).post_init(post_init).build()

app.add_handler(CommandHandler("clear", clear))
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("use_gpt3", use_gpt3))
app.add_handler(CommandHandler("use_gpt4", use_gpt4))
app.add_handler(CommandHandler("show_cost", show_cost))
app.add_handler(CommandHandler("hide_cost", hide_cost))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))
app.add_handler(MessageHandler(filters.VOICE, transcribe_audio))

app.run_polling()
