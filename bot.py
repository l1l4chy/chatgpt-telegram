import os
from dotenv import load_dotenv
import openai
from functools import wraps
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters

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

@restricted
async def message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_input = update.message.text

    blank_chat_history = [
      {"role": "system", "content": "You are a helpful assistant."}
    ]

    # retrieve chat history, if there is none, use the blank chat history
    chat_history = context.chat_data.get('history', blank_chat_history)

    # append user input to chat history
    chat_history.append({"role": "user", "content": user_input})

    response = openai.ChatCompletion.create(
      model="gpt-3.5-turbo",
      messages=chat_history,
    )

    # append response to chat history
    chat_history.append({ "role": "assistant", "content": response.choices[0].message.content })

    # update chat history
    context.chat_data['history'] = chat_history

    await update.message.reply_text(response.choices[0].message.content)

@restricted
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['history'] = []
    await update.message.reply_text('Chat history cleared.')

app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_API_TOKEN")).build()

app.add_handler(CommandHandler("clear", clear))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))

app.run_polling()
