import logging
import socket
import asyncio
import multiprocessing
import detector
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram import Update

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)


class BotState:
    def __init__(self):
        self.running = False
        self.receive_task = None
        self.server_socket, self.stopping_socket = self.initialization()

    def initialization(self, port1=12345, port2=12346):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        server_socket.bind(('localhost', port1))
        server_socket.setblocking(False)
        stopping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        stopping_socket.bind(('localhost', port2))
        stopping_socket.listen(1)
        return server_socket, stopping_socket


async def receive_image(server_socket):
    image_data = b""
    client_addr = None
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
    bot_state = context.bot_data.get('bot_state')
    if bot_state.running:
        await update.message.reply_text('Already running.')
        return

    bot_state.running = True
    await update.message.reply_text('Starting...')

    sub = multiprocessing.Process(target=detector.run)
    sub.start()

    bot_state.receive_task = asyncio.create_task(receive_loop(update, bot_state))


async def receive_loop(update, bot_state):
    while bot_state.running:
        try:
            image_data, client_addr = await receive_image(bot_state.server_socket)
            await update.message.reply_text(f'Face detected from {client_addr}')
            await update.message.reply_photo(image_data)
        except asyncio.CancelledError:
            break
        except Exception as e:
            logging.error(f"Error in receive_loop: {e}")
            break


async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    bot_state = context.bot_data.get('bot_state')
    if not bot_state.running:
        await update.message.reply_text('Not running.')
        return

    bot_state.running = False

    if bot_state.receive_task:
        bot_state.receive_task.cancel()
        try:
            await bot_state.receive_task
        except asyncio.CancelledError:
            pass

    try:
        client_conn, _ = await asyncio.get_event_loop().sock_accept(bot_state.stopping_socket)
        await asyncio.get_event_loop().sock_sendall(client_conn, b'stop')
        client_conn.close()
    except Exception as e:
        logging.error(f"Error sending stop signal: {e}")

    await update.message.reply_text('Stopping...')
    await update.message.reply_text('Stopped.')


def main() -> None:
    telegram_bot_token = 'YOUR_BOT_TOKEN'
    application = Application.builder().token(telegram_bot_token).build()

    bot_state = BotState()
    application.bot_data['bot_state'] = bot_state

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.run_polling()


if __name__ == '__main__':
    main()
