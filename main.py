import cv2
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.clock import Clock
from kivy.graphics.texture import Texture
import pygame
from pyzbar.pyzbar import decode

# Initialize valid and found barcode lists
valid_barcodes_list = ['123456789012', '987654321098']
found_barcodes_list = []

class CameraApp(App):
    def build(self):
        # Define the layout
        self.layout = BoxLayout(orientation='vertical')

        # Add camera feed
        self.image = Image(size_hint=(1, 0.8))  # Make the camera feed take up most of the screen
        self.layout.add_widget(self.image)

        # Label to show messages
        self.label = Label(text="Point the camera at a barcode.", size_hint=(1, 0.1))
        self.layout.add_widget(self.label)

        # Button to clear found barcodes
        self.clear_found_btn = Button(text="Clear Found Barcodes", size_hint=(1, 0.05))
        self.clear_found_btn.bind(on_press=self.clear_found_barcodes)
        self.layout.add_widget(self.clear_found_btn)

        # TextInput for manually adding barcodes
        self.manual_input = TextInput(hint_text="Enter barcode (order-line)", multiline=False, size_hint=(1, 0.05))
        self.layout.add_widget(self.manual_input)

        # Button to add barcode manually to the valid list
        self.add_barcode_btn = Button(text="Add Barcode to Valid List", size_hint=(1, 0.05))
        self.add_barcode_btn.bind(on_press=self.add_manual_barcode)
        self.layout.add_widget(self.add_barcode_btn)

        # Camera feed setup
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

        return self.layout

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            # Decode barcodes
            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')

                # Check against the valid barcodes list
                if barcode_data in valid_barcodes_list:
                    if barcode_data not in found_barcodes_list:
                        found_barcodes_list.append(barcode_data)
                        self.play_sound("linuxmint-login.wav")
                        self.label.text = f"Barcode {barcode_data} added to found list!"
                    else:
                        self.label.text = f"Barcode {barcode_data} already found."
                else:
                    self.play_sound("linuxmint-gdm.wav")
                    self.label.text = f"Barcode {barcode_data} not found in valid list."

            # Convert frame to Kivy texture
            buffer = cv2.flip(frame, 0).tostring()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture

    def play_sound(self, sound_file):
        try:
            pygame.mixer.init()
            pygame.mixer.music.load(sound_file)
            pygame.mixer.music.play()
        except Exception as e:
            print(f"Error playing sound: {e}")

    def clear_found_barcodes(self, instance):
        found_barcodes_list.clear()
        self.label.text = "Found barcodes list cleared."

    def add_manual_barcode(self, instance):
        barcode = self.manual_input.text
        if barcode:
            valid_barcodes_list.append(barcode)
            self.label.text = f"Barcode {barcode} added to valid list."
            self.manual_input.text = ""  # Clear input field after adding
        else:
            self.label.text = "Please enter a valid barcode before adding."

# Run the app
if __name__ == '__main__':
    CameraApp().run()
