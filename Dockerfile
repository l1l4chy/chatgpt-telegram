FROM python:3.8

WORKDIR /app

# install ffmpeg
RUN apt-get update && apt-get install -y ffmpeg

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the source code
COPY . .

CMD ["python", "bot.py"]
