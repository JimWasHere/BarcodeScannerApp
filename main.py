import cv2
import numpy as np
from kivy.app import App
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from pyzbar.pyzbar import decode
import pygame  # For sound playback

# Define two lists for checking barcodes
valid_barcodes_list = ['123456789012', '987654321098', '6175111500-35', '4005123600-13' ,'2834113300-19']  # Example barcodes
moved_barcodes_list = []  # List to hold moved barcodes

class CameraApp(App):
    def build(self):
        # Set up the layout
        self.layout = BoxLayout(orientation='vertical')

        # Camera feed display
        self.img = Image()
        self.layout.add_widget(self.img)

        # Label to show barcodes found
        self.barcode_label = Label(text="Barcodes Found:\n", size_hint=(1, 0.2))
        self.layout.add_widget(self.barcode_label)

        # Initialize the camera
        self.cap = cv2.VideoCapture(0, cv2.CAP_V4L2)
        if not self.cap.isOpened():
            self.barcode_label.text = "Error: Could not open video device."
            print("Error: Could not open video device.")
        else:
            print("Camera opened successfully.")
            Clock.schedule_interval(self.update, 1.0 / 30.0)  # Update the frame every 30th of a second

        return self.layout

    def update(self, dt):
        # Capture frame from the camera
        ret, frame = self.cap.read()

        if ret:
            # Decode barcodes in the current frame
            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                barcode_type = barcode.type

                if barcode_data in valid_barcodes_list:
                    print(f"Barcode {barcode_data} found in the valid list")
                    self.play_sound("linuxmint-login.wav")
                    self.move_to_list(barcode_data)

                    # Update the barcode label
                    self.barcode_label.text = f"Barcodes Found:\n" + "\n".join(moved_barcodes_list)
                else:
                    print(f"Barcode {barcode_data} not found in any list")
                    self.play_sound("linuxmint-gdm.wav")

                # Draw a rectangle around the barcode
                points = barcode.polygon
                if len(points) == 4:
                    pts = [tuple(point) for point in points]
                    cv2.polylines(frame, [np.array(pts, dtype=np.int32)], isClosed=True, color=(0, 255, 0), thickness=3)
                else:
                    cv2.rectangle(frame, (barcode.rect.left, barcode.rect.top),
                                  (barcode.rect.left + barcode.rect.width, barcode.rect.top + barcode.rect.height),
                                  (0, 255, 0), 2)

                # Display the barcode data on the frame
                text = f'{barcode_type}: {barcode_data}'
                cv2.putText(frame, text, (barcode.rect.left, barcode.rect.top - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

            # Convert the image to Kivy texture and display it
            buf = cv2.flip(frame, 0).tostring()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buf, colorfmt='bgr', bufferfmt='ubyte')
            self.img.texture = texture

    def play_sound(self, sound_file):
        """Play a sound when a barcode is detected."""
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
            print(f"Playing sound: {sound_file}")
        except Exception as e:
            print(f"Error playing sound: {e}")

    def move_to_list(self, barcode_data):
        """Move the item (barcode) to the moved list."""
        valid_barcodes_list.remove(barcode_data)
        moved_barcodes_list.append(barcode_data)
        print(f"Moved {barcode_data} to the moved list")

    def on_stop(self):
        """Release the camera when the app is closed."""
        self.cap.release()

# Run the Kivy app
if __name__ == '__main__':
    CameraApp().run()
