"""
Telegram Bot Server for Face Detection

This script implements a Telegram bot server that integrates with a face detection system.
It handles starting and stopping the detection process, receives detected face images,
and sends them to the Telegram chat.

Author: Marc'Antonio Lopez
Date: 2024-07-04
"""

import logging
import socket
import asyncio
import multiprocessing
import sys
import time
import detector
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class BotState:
    """
    Class to manage the state of the Telegram bot and associated sockets.
    """

    def __init__(self, config):
        """
        Initialize the BotState with the given configuration.

        Args:
            config (dict): Configuration dictionary containing server addresses and ports.
        """
        self.running = False
        self.receive_task = None
        self.config = config
        self.server_socket, self.stopping_socket, self.interface_socket = self.initialization()
        self.detector_process = None

    def initialization(self):
        """
        Initialize the sockets for communication.

        Returns:
            tuple: A tuple containing the server socket, stopping socket, and interface socket.
        """
        # Set up UDP server socket for receiving images
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind((self.config['server_addr'], self.config['server_port']))
        server_socket.setblocking(False)

        # Set up TCP server socket for stopping the detector
        stopping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stopping_socket.bind((self.config['stopping_addr'], self.config['stopping_port']))
        stopping_socket.listen(1)

        # Set up TCP client socket for interface communication
        interface_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        interface_socket.connect((self.config['interface_addr'], self.config['interface_port']))
        interface_socket.setblocking(False)
        interface_socket.sendall(b'ok')

        return server_socket, stopping_socket, interface_socket

    def cleanup(self):
        """
        Clean up resources by closing sockets and terminating the detector process.
        """
        if self.server_socket:
            self.server_socket.close()
        if self.stopping_socket:
            self.stopping_socket.close()
        if self.interface_socket:
            self.interface_socket.close()
        if self.detector_process:
            self.detector_process.terminate()
            self.detector_process.join(timeout=5)
            if self.detector_process.is_alive():
                self.detector_process.kill()


async def receive_image(bot_state):
    """
    Receive image data from the UDP socket.

    Args:
        bot_state (BotState): The current state of the bot.

    Returns:
        tuple: A tuple containing the image data and client address.
    """
    image_data = b""
    client_addr = None

    while True:
        try:
            packet, client_addr = await asyncio.get_running_loop().sock_recvfrom(bot_state.server_socket, 65535)
            if not packet:
                break
            image_data += packet
        except BlockingIOError:
            await asyncio.sleep(0.1)
            continue
        except asyncio.CancelledError:
            break

    return image_data, client_addr


async def receive_commands(bot_state):
    """
    Receive commands from the interface socket.

    Args:
        bot_state (BotState): The current state of the bot.
    """
    try:
        msg = await asyncio.get_running_loop().sock_recv(bot_state.interface_socket, 1024)
        if msg == b'stop':
            bot_state.running = False
            bot_state.server_socket.close()
            bot_state.stopping_socket.close()
            bot_state.interface_socket.close()
            sys.exit(0)
    except BlockingIOError:
        pass
    except Exception as e:
        logging.error(f"Error receiving command: {e}")


async def receive_loop(update, bot_state):
    """
    Main loop for receiving images and commands.

    Args:
        update (Update): The Telegram update object.
        bot_state (BotState): The current state of the bot.
    """
    while bot_state.running:
        image_task = asyncio.create_task(receive_image(bot_state))
        command_task = asyncio.create_task(receive_commands(bot_state))

        done, pending = await asyncio.wait(
            [image_task, command_task],
            return_when=asyncio.FIRST_COMPLETED
        )

        for task in pending:
            task.cancel()

        if image_task in done:
            try:
                image_data, client_addr = image_task.result()
                if image_data:
                    await update.message.reply_text(f'Face detected from {client_addr}')
                    await update.message.reply_photo(image_data)
            except Exception as e:
                logging.error(f"Error processing image: {e}")

        if command_task in done:
            try:
                command_task.result()
            except Exception as e:
                logging.error(f"Error processing command: {e}")

        await asyncio.sleep(0.1)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /start command.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): The context object for the handler.
    """
    bot_state = context.bot_data.get('bot_state')
    if bot_state.running:
        await update.message.reply_text('Already running.')
        return

    bot_state.interface_socket.sendall(b'running')

    bot_state.running = True
    await update.message.reply_text('Starting...')

    bot_state.detector_process = multiprocessing.Process(target=detector.run)
    bot_state.detector_process.start()

    bot_state.receive_task = asyncio.create_task(receive_loop(update, bot_state))


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handler for the /stop command.

    Args:
        update (Update): The Telegram update object.
        context (ContextTypes.DEFAULT_TYPE): The context object for the handler.
    """
    bot_state = context.bot_data.get('bot_state')
    if not bot_state.running:
        await update.message.reply_text('Not running.')
        return

    bot_state.running = False

    try:
        bot_state.interface_socket.sendall(b'stopping')
    except socket.error:
        logging.error("Error sending stopping signal to interface")

    if bot_state.receive_task:
        bot_state.receive_task.cancel()
        try:
            await bot_state.receive_task
        except asyncio.CancelledError:
            pass

    bot_state.cleanup()

    try:
        client_conn, _ = await asyncio.get_event_loop().sock_accept(bot_state.stopping_socket)
        await asyncio.get_event_loop().sock_sendall(client_conn, b'stop')
        client_conn.close()
    except Exception as e:
        logging.error(f"Error sending stop signal: {e}")

    await update.message.reply_text('Stopping...')
    await update.message.reply_text('Stopped.')


def run(config) -> None:
    """
    Main function to run the Telegram bot.

    Args:
        config (dict): Configuration dictionary containing the bot token and server settings.
    """
    telegram_bot_token = config['bot_token']
    application = Application.builder().token(telegram_bot_token).build()

    bot_state = BotState(config)
    application.bot_data['bot_state'] = bot_state

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))

    try:
        application.run_polling()
    finally:
        bot_state.cleanup()


if __name__ == '__main__':
    run(config={
        "bot_token": "YOUR_BOT_TOKEN_HERE",
        "server_addr": "localhost",
        "server_port": 12345,
        "stopping_addr": "localhost",
        "stopping_port": 12346,
        "interface_addr": "localhost",
        "interface_port": 12347
    })
