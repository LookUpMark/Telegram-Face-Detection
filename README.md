# Telegram Face Detection

This project implements a Telegram bot that performs real-time face detection using a webcam. The system combines a Telegram bot server with integrated face detection capabilities.

## Features

- Real-time face detection using OpenCV
- Telegram bot interface for starting and stopping the detection process
- Sends images with detected faces to a Telegram chat every 5 seconds (editable)
- Configurable via variables

## Prerequisites

- Python 3.7+
- OpenCV
- python-telegram-bot
- A Telegram Bot Token (obtain from [@BotFather](https://t.me/botfather))

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/LookUpMark/Telegram-Face-Detection.git
   cd Telegram-Face-Detection
   ```

2. Install the required packages:
   ```
   pip install -r requirements.txt
   ```

3. Set up your Telegram Bot Token:
   - Create a `.env` file in the project root
   - Modify the following line, replacing `YOUR_BOT_TOKEN` with your actual token:
     ```
     telegram_bot_token=YOUR_BOT_TOKEN
     ```

## Usage

1. Start the Telegram bot server:
   ```
   python telegram_bot_server.py
   ```

2. In your Telegram app, start a chat with your bot and use the following commands:
   - `/start`: Begin face detection and image sending
   - `/stop`: Stop face detection and image sending

## Configuration

You can modify the following variables in `telegram_bot_server.py` to customize behavior:

- `server_addr` and `server_port`: UDP server address (default: 'localhost', 12345)
- `stopping_addr` and `stopping_port`: TCP server address (default: 'localhost', 12346)

In `detector.py` you can modify the following variable:

- `image_send_interval`: Minimum interval between image sends in seconds (default: 5)

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
