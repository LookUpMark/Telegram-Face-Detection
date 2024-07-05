"""
Face Detection UDP Client

This script implements a face detection system using OpenCV. It captures
video from a webcam, detects faces, and sends images with detected faces
to a UDP server every 5 seconds.

The script can be stopped remotely via a TCP connection.

Author: Marc'Antonio Lopez
Date: 2024-07-04
"""

import time
import cv2
import socket
import threading
import asyncio

running = True
last_sent_time = 0


def stopping():
    """
    Listen for a stop signal on a TCP socket.

    This function runs in a separate thread and sets the global 'running'
    variable to False when a stop signal is received.
    """
    global running
    stopping_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    stopping_socket.connect(('localhost', 12346))

    while running:
        try:
            data = stopping_socket.recv(1024)
            if data == b'stop':
                running = False
                break
        except Exception as e:
            print(f"Error in stopping thread: {e}")
            break

    stopping_socket.close()


def send_image(frame, client_socket, server_addr, image_send_interval=5):
    """
    Send an image to the UDP server if 5 seconds have passed since the last send.

    Args:
        frame (numpy.ndarray): The image frame to send.
        client_socket (socket.socket): The UDP client socket.
        server_addr (tuple): The address of the UDP server.
        image_send_interval (int, optional): The interval in seconds between image sends. Defaults to 5.
    """
    global last_sent_time
    current_time = time.time()

    if current_time - last_sent_time < image_send_interval:
        return  # Don't send if less than 5 seconds have passed since the last send

    img_bytes = cv2.imencode('.jpg', frame)[1].tobytes()

    chunk_size = 1024
    for i in range(0, len(img_bytes), chunk_size):
        chunk = img_bytes[i:i + chunk_size]
        client_socket.sendto(chunk, server_addr)

    client_socket.sendto(b'', server_addr)
    print("Image sent successfully")
    last_sent_time = current_time


def detect_faces(frame, face_cascade):
    """
    Detect faces in the given frame using the provided face cascade classifier.

    Args:
        frame (numpy.ndarray): The image frame to detect faces in.
        face_cascade (cv2.CascadeClassifier): The face cascade classifier.

    Returns:
        tuple: A tuple containing the frame with detected faces drawn and a boolean
               indicating whether any faces were detected.
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray_equalized = cv2.equalizeHist(gray)

    faces = face_cascade.detectMultiScale(gray_equalized, scaleFactor=1.3, minNeighbors=5, minSize=(30, 30))

    for (x, y, w, h) in faces:
        cv2.rectangle(frame, (x, y), (x + w, y + h), (255, 0, 0), 2)

    return frame, len(faces) > 0


async def capture_frames(client_socket, server_addr):
    """
    Capture frames from the webcam, detect faces, and send images with faces.

    This function runs the main loop for capturing video frames, detecting faces,
    and sending images to the UDP server.

    Args:
        client_socket (socket.socket): The UDP client socket.
        server_addr (tuple): The address of the UDP server.
    """
    global running

    face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
    cap = cv2.VideoCapture(0)

    if not cap.isOpened():
        print("Error: Unable to open webcam")
        return

    while running:
        ret, frame = cap.read()

        if not ret:
            print("Error: Unable to capture frame")
            break

        frame_with_faces, faces_detected = detect_faces(frame, face_cascade)
        if faces_detected:
            send_image(frame_with_faces, client_socket, server_addr)

        await asyncio.sleep(0.1)  # Small delay to prevent CPU overuse

    cap.release()
    cv2.destroyAllWindows()


def run():
    """
    Main function to set up and run the face detection system.
    """
    global running
    running = True

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_addr = ('localhost', 12345)

    stopping_thread = threading.Thread(target=stopping)
    stopping_thread.start()

    asyncio.run(capture_frames(client_socket, server_addr))

    client_socket.close()
    print("Detector stopped")


if __name__ == "__main__":
    run()
