import os
from dotenv import load_dotenv
import openai
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes
from telegram.ext import filters

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

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

async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.chat_data['history'] = []
    await update.message.reply_text('Chat history cleared.')

app = ApplicationBuilder().token(os.getenv("TELEGRAM_BOT_API_TOKEN")).build()

app.add_handler(CommandHandler("clear", clear))
app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), message))

app.run_polling()
