# ChatGPT telegram bot script using API

This is a telegram bot that uses the [ChatGPT](https://platform.openai.com/docs/guides/chat) API to generate responses to messages.


## Setup

### Docker

Build the docker image:

```
docker build -t chatgpt-telegram-bot .
```

Run the docker image:

```
docker run -d --name chatgpt-telegram-bot chatgpt-telegram-bot
```

### Manually
Install dependencies:
- Python 3
- pip

Install dependencies using pip:
- pip install python-telegram-bot
- pip install openai
- pip install python-dotenv


### Environment variables

The bot uses environment variables to store the telegram bot token and the OpenAI API key. You can create a `.env` file in the root directory of the project and add the following variables:

```
TELEGRAM_BOT_API_TOKEN=your_telegram_token
OPENAI_API_KEY=your_openai_api_key
```

## Usage

Run the bot using the following command:

```
python bot.py
```

### Commands

- `/clear` - Clear the conversation history for chatgpt (but not in telegram chat).


### Restrict access to the bot

You can restrict access to the bot by adding a list of telegram user ids to the `ALLOWED_USER_IDS` variable in the `.env` file. The bot will only respond to messages from users in the list.

```
ALLOWED_USER_IDS=123456789,987654321
```
