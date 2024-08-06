"""
Face Recognition GUI Application

This script implements a graphical user interface for the Face Recognition system
using the Flet framework. It allows users to start and stop the face detection process,
and configure various settings.

Author: Marc'Antonio Lopez
Date: 2024-07-04
"""

import flet as ft
import socket
import multiprocessing
import threading
import telegram_bot_server
import time
from flet import Row, Column, TextField, ElevatedButton, Text
from flet_core.control_event import ControlEvent

# Global variable to control the running state
running = True


def main(page: ft.Page) -> None:
    """
    Main function to set up and run the Face Recognition GUI application.

    Args:
        page (ft.Page): The main page of the Flet application.
    """
    global running
    client_socket = None
    socket_server = None
    bot_process = None
    comm_thread = None

    # Set up the page
    page.title = "Face Recognition"
    page.vertical_alignment = ft.MainAxisAlignment.CENTER
    page.horizontal_alignment = ft.CrossAxisAlignment.CENTER

    def communication(client_socket) -> None:
        """
        Handle communication with the client socket.

        This function runs in a separate thread and updates the GUI based on
        messages received from the client socket.

        Args:
            client_socket (socket.socket): The client socket for communication.
        """
        global running
        while running:
            try:
                msg = client_socket.recv(1024).decode()
                if msg == "running":
                    status.value = "Start signal received, program running..."
                    status.color = "green"
                    page.update()
                elif msg == "stopping":
                    status.value = "Stop signal received, program stopping..."
                    status.color = "red"
                    page.update()
                    running = False
                    break
            except socket.error as e:
                if not running:
                    print("Communication thread exiting normally")
                else:
                    print(f"Error in communication: {e}")
                break
        print("Communication thread exiting")

    def start(e: ControlEvent) -> None:
        """
        Start the face detection process.

        This function is called when the Start button is clicked.

        Args:
            e (ControlEvent): The button click event.
        """
        nonlocal client_socket, socket_server, bot_process, comm_thread
        global running
        running = True

        # Collect configuration from text fields
        config = {
            "bot_token": tf1.value,
            "server_addr": tf2.value,
            "server_port": int(tf3.value),
            "stopping_addr": tf4.value,
            "stopping_port": int(tf5.value),
            "interface_addr": tf6.value,
            "interface_port": int(tf7.value)
        }

        # Set up the socket server
        socket_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        socket_server.bind((config["interface_addr"], config["interface_port"]))
        socket_server.listen(1)

        # Start the Telegram bot process
        bot_process = multiprocessing.Process(target=telegram_bot_server.run, args=(config,))
        bot_process.start()

        # Accept connection from the client
        client_socket, _ = socket_server.accept()

        # Update GUI
        b1.disabled = True
        b2.disabled = False
        page.update()

        # Wait for "ok" message from client
        msg = client_socket.recv(1024)
        if msg.decode() == "ok":
            status.value = "Program running, waiting for start signal..."
            status.color = "yellow"
            page.update()
            comm_thread = threading.Thread(target=communication, args=(client_socket,))
            comm_thread.start()

    def stop(e: ControlEvent) -> None:
        """
        Stop the face detection process.

        This function is called when the Stop button is clicked.

        Args:
            e (ControlEvent): The button click event.
        """
        global running
        nonlocal client_socket, socket_server, bot_process, comm_thread
        running = False

        # Send stop signal to client
        if client_socket:
            try:
                client_socket.sendall(b'stop')
            except socket.error:
                pass
            time.sleep(0.5)
            client_socket.close()

        # Close sockets and terminate processes
        if socket_server:
            socket_server.close()

        if bot_process:
            bot_process.terminate()
            for _ in range(10):
                if not bot_process.is_alive():
                    break
                time.sleep(0.5)
            if bot_process.is_alive():
                bot_process.kill()

        if comm_thread:
            comm_thread.join(timeout=5)

        if client_socket:
            client_socket.close()
        if socket_server:
            socket_server.close()

        # Update GUI
        b1.disabled = False
        b2.disabled = True
        status.value = "Program not running"
        status.color = "red"
        page.update()

    # Create GUI elements
    tf1 = TextField(label="Telegram bot token", width=400, expand=True)
    tf2 = TextField(label="Bot server address", value="localhost", expand=True)
    tf3 = TextField(label="Bot server port", value="12345", expand=True)
    tf4 = TextField(label="Stopping server address", value="localhost", expand=True)
    tf5 = TextField(label="Stopping server port", value="12346", expand=True)
    tf6 = TextField(label="Interface address", value="localhost", expand=True)
    tf7 = TextField(label="Interface port", value="12347", expand=True)
    b1 = ElevatedButton("Start", on_click=start, disabled=False)
    b2 = ElevatedButton("Stop", on_click=stop, disabled=True, bgcolor="red")
    status = Text(value="Program not running", color="red")

    # Add elements to the page
    page.add(
        Column([
            Row([tf1], width=400, alignment=ft.MainAxisAlignment.CENTER),
            Row([tf2, tf3], width=400, alignment=ft.MainAxisAlignment.CENTER),
            Row([tf4, tf5], width=400, alignment=ft.MainAxisAlignment.CENTER),
            Row([tf6, tf7], width=400, alignment=ft.MainAxisAlignment.CENTER),
            Row([b1, b2], width=400, alignment=ft.MainAxisAlignment.CENTER),
            Row([status], width=400, alignment=ft.MainAxisAlignment.CENTER)
        ], alignment=ft.MainAxisAlignment.CENTER)
    )

    page.update()


if __name__ == "__main__":
    ft.app(target=main)
