import cv2
import numpy as np
from kivy.app import App
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from pyzbar.pyzbar import decode


class CameraApp(App):
    def build(self):
        # Layout setup
        self.layout = Image(size_hint=(1, 1))
        # Camera feed setup
        self.capture = cv2.VideoCapture(0)  # Open the camera
        Clock.schedule_interval(self.update, 1.0 / 30.0)  # Update frame every 1/30 second
        self.previous_barcodes = set()  # Keep track of seen barcodes

        return self.layout

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            # Barcode decoding
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                barcode_data = obj.data.decode('utf-8')

                # Check if the barcode has already been seen
                if barcode_data not in self.previous_barcodes:
                    self.previous_barcodes.add(barcode_data)

                    # Draw a rectangle around the barcode
                    points = obj.polygon
                    if len(points) == 4:
                        pts = points
                    else:
                        pts = cv2.convexHull(np.array([point for point in points], dtype=np.int32))
                    cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

                    # Display barcode data
                    barcode_type = obj.type
                    print(f"Detected barcode: {barcode_data}, Type: {barcode_type}")

            # Convert frame to Kivy texture
            buffer = cv2.flip(frame, 0).tostring()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
            self.layout.texture = texture

    def on_stop(self):
        # Release the camera feed properly when the app is closed
        if self.capture.isOpened():
            self.capture.release()


if __name__ == '__main__':
    CameraApp().run()
