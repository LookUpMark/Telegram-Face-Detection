# Telegram Face Detection

This project implements a Telegram bot that performs real-time face detection using a webcam. The system combines a Telegram bot server with integrated face detection capabilities and a graphical user interface for easy control.

## Features

- Real-time face detection using OpenCV
- Telegram bot interface for starting and stopping the detection process
- Sends images with detected faces to a Telegram chat every 5 seconds (configurable)
- Graphical user interface for easy configuration and control
- Configurable server addresses and ports

## Prerequisites

- Python 3.7+
- OpenCV
- python-telegram-bot
- Flet (for GUI)
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

## Usage

1. Start the graphical user interface:
   ```
   python main.py
   ```

2. In the GUI:
   - Enter your Telegram Bot Token
   - Configure server addresses and ports if needed (defaults should work for most cases)
   - Click the "Start" button to begin face detection

3. In your Telegram app, start a chat with your bot and use the following commands:
   - `/start`: Begin face detection and image sending
   - `/stop`: Stop face detection and image sending

4. To stop the program, click the "Stop" button in the GUI

## Configuration

You can modify the following settings in the GUI:

- Telegram bot token
- Bot server address and port
- Stopping server address and port
- Interface address and port

In `detector.py` you can modify the following variable:

- `image_send_interval`: Minimum interval between image sends in seconds (default: 5)

## Project Structure

- `main.py`: Graphical user interface implementation
- `telegram_bot_server.py`: Telegram bot server implementation
- `detector.py`: Face detection implementation
- `requirements.txt`: List of Python dependencies

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
