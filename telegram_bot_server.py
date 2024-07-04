"""
Telegram Bot with UDP Server for Face Detection

This script implements a Telegram bot that receives images from a UDP server
and forwards them to a Telegram chat. It also manages the start and stop
of a face detection process.

The bot responds to two commands:
- /start: Starts the face detection process
- /stop: Stops the face detection process

Author: Marc'Antonio Lopez
Date: 2024-07-04
"""

import logging
import socket
import asyncio
import multiprocessing
import detector
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def initialization():
    """
    Initialize UDP server socket and TCP stopping socket.

    Returns:
        tuple: A tuple containing the server socket and stopping socket.
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(('localhost', 12345))
    server_socket.setblocking(False)
    stopping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stopping_socket.bind(('localhost', 12346))
    stopping_socket.listen(1)
    return server_socket, stopping_socket


async def receive_image(server_socket):
    """
    Receive image data from the UDP server socket.

    Args:
        server_socket (socket.socket): The UDP server socket.

    Returns:
        tuple: A tuple containing the image data and client address.
    """
    image_data = b""
    while True:
        try:
            packet, client_addr = await asyncio.get_running_loop().sock_recvfrom(server_socket, 65535)
            if not packet:
                break
            image_data += packet
        except asyncio.CancelledError:
            break
    return image_data, client_addr


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /start command.

    This function starts the face detection process and begins receiving images.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    global running, server_socket, receive_task
    if running:
        await update.message.reply_text('Already running.')
        return

    running = True
    await update.message.reply_text('Starting...')

    # Start the detector process
    sub = multiprocessing.Process(target=detector.run)
    sub.start()

    # Start receiving images
    receive_task = asyncio.create_task(receive_loop(update))


async def receive_loop(update):
    """
    Main loop for receiving and forwarding images.

    This function continuously receives images from the UDP server
    and forwards them to the Telegram chat.

    Args:
        update (Update): The update object from Telegram.
    """
    global running, server_socket
    while running:
        try:
            image_data, client_addr = await receive_image(server_socket)
            await update.message.reply_text(f'Received image from {client_addr}')
            await update.message.reply_photo(image_data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error in receive_loop: {e}")
            break


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle the /stop command.

    This function stops the face detection process and image receiving.

    Args:
        update (Update): The update object from Telegram.
        context (ContextTypes.DEFAULT_TYPE): The context object from Telegram.
    """
    global running, receive_task, stopping_socket

    if not running:
        await update.message.reply_text('Not running.')
        return

    running = False

    if receive_task:
        receive_task.cancel()
        try:
            await receive_task
        except asyncio.CancelledError:
            pass

    try:
        # Send stop signal to the detector process
        client_conn, _ = await asyncio.get_event_loop().sock_accept(stopping_socket)
        await asyncio.get_event_loop().sock_sendall(client_conn, b'stop')
        client_conn.close()
    except Exception as e:
        logging.error(f"Error sending stop signal: {e}")

    await update.message.reply_text('Stopping...')
    await update.message.reply_text('Stopped.')


def main() -> None:
    """
    Main function to set up and run the Telegram bot.
    """
    application = Application.builder().token('YOUR_BOT_TOKEN').build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.run_polling()


if __name__ == '__main__':
    running = False
    receive_task = None
    server_socket, stopping_socket = initialization()
    main()