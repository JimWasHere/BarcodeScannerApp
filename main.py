import cv2
import json
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.textinput import TextInput
from kivy.uix.image import Image
from kivy.uix.popup import Popup
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from pyzbar.pyzbar import decode
from kivy.core.audio import SoundLoader  # For playing sounds

# File to save/load the location data
LOCATION_FILE = "locations.json"

# Dictionary to hold locations and corresponding barcodes
location_dict = {}

class CameraApp(App):
    def build(self):
        # Load saved location data (if available)
        self.load_location_data()

        # Layout setup
        self.layout = BoxLayout(orientation='vertical')

        # Add camera feed
        self.image = Image(size_hint=(1, 0.8))
        self.layout.add_widget(self.image)

        # Label for showing messages
        self.label = Label(text="Set a location or scan a barcode", size_hint=(1, 0.1))
        self.layout.add_widget(self.label)

        # Text input for location and barcode entry
        self.text_input = TextInput(hint_text="Enter location or barcode", multiline=False, size_hint=(1, 0.05))
        self.layout.add_widget(self.text_input)

        # Button to set location
        self.set_location_btn = Button(text="Set Location", size_hint=(1, 0.05))
        self.set_location_btn.bind(on_press=self.set_location)
        self.layout.add_widget(self.set_location_btn)

        # Button to find barcode
        self.find_barcode_btn = Button(text="Find Barcode", size_hint=(1, 0.05))
        self.find_barcode_btn.bind(on_press=self.find_barcode)
        self.layout.add_widget(self.find_barcode_btn)

        # Camera feed setup
        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

        # Track the current mode (True for adding barcodes, False for finding barcodes)
        self.adding_to_location = False

        # Load sound files
        self.success_sound = SoundLoader.load('linuxmint-login.wav')
        self.error_sound = SoundLoader.load('linuxmint-gdm.wav')

        return self.layout

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            # Decode barcodes
            barcodes = decode(frame)
            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                self.text_input.text = barcode_data  # Display scanned barcode in text input

                # Add delay of 0.5 seconds to prevent duplicate scans
                Clock.schedule_once(lambda dt: self.process_barcode(barcode_data), 0.5)

            # Convert frame to Kivy texture
            buffer = cv2.flip(frame, 0).tostring()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
            self.image.texture = texture

    def process_barcode(self, barcode_data):
        if self.adding_to_location and self.current_location:
            self.add_barcode_to_location(barcode_data)

    def set_location(self, instance):
        location = self.text_input.text
        if len(location) > 4:  # If location input has more than 4 characters, show confirmation popup
            popup_content = BoxLayout(orientation='vertical')
            popup_content.add_widget(Label(text=f"Location '{location}' is longer than 4 characters. Is this correct?"))
            confirm_button = Button(text="Yes", size_hint=(1, 0.2))
            confirm_button.bind(on_press=lambda x: self.confirm_set_location(location))
            popup_content.add_widget(confirm_button)

            cancel_button = Button(text="No", size_hint=(1, 0.2))
            cancel_button.bind(on_press=lambda x: self.close_popup())
            popup_content.add_widget(cancel_button)

            self.popup = Popup(title='Confirm Location', content=popup_content, size_hint=(0.75, 0.4))
            self.popup.open()
        else:
            self.confirm_set_location(location)

    def confirm_set_location(self, location):
        self.current_location = location
        self.label.text = f"Location set to {self.current_location}. Now scanning barcodes."
        self.text_input.text = ""
        self.adding_to_location = True  # Enable barcode adding mode
        if hasattr(self, 'popup'):
            self.popup.dismiss()

    def close_popup(self):
        """Closes the popup and ensures the app stays responsive."""
        if hasattr(self, 'popup'):
            self.popup.dismiss()
        self.text_input.focus = True  # Refocus on the text input to resume interaction

    def add_barcode_to_location(self, barcode):
        if not self.current_location:
            self.label.text = "No location set. Please set a location first."
            return

        # Check if the barcode exists in any other location
        found_in_other_location = None
        for location, barcodes in location_dict.items():
            if barcode in barcodes and location != self.current_location:
                found_in_other_location = location
                break

        if found_in_other_location:
            # Barcode found in another location, prompt to move
            self.show_move_popup(barcode, found_in_other_location)
        else:
            # If the barcode is already in the current location
            if self.current_location in location_dict:
                if barcode in location_dict[self.current_location]:
                    self.label.text = f"Barcode {barcode} already in {self.current_location}."
                    self.error_sound.play()  # Play error sound
                else:
                    location_dict[self.current_location].append(barcode)
                    self.label.text = f"Barcode {barcode} added to {self.current_location}."
                    self.success_sound.play()  # Play success sound
            else:
                location_dict[self.current_location] = [barcode]
                self.label.text = f"Barcode {barcode} added to new location {self.current_location}."
                self.success_sound.play()  # Play success sound

            self.text_input.text = ""  # Clear the input after adding
            self.save_location_data()

    def show_move_popup(self, barcode, found_in_location):
        """Shows a popup asking the user if they want to move the barcode."""
        popup_content = BoxLayout(orientation='vertical')
        popup_content.add_widget(
            Label(text=f"Barcode {barcode} is in {found_in_location}. Move to {self.current_location}?"))

        # Buttons for confirmation (Yes/No)
        yes_button = Button(text="Yes", size_hint=(1, 0.2))
        yes_button.bind(on_press=lambda x: self.move_barcode(barcode, found_in_location))
        yes_button.bind(on_press=lambda x: self.close_popup())  # Close the popup after moving
        popup_content.add_widget(yes_button)

        no_button = Button(text="No", size_hint=(1, 0.2))
        no_button.bind(on_press=lambda x: self.close_popup())  # Close the popup without moving
        popup_content.add_widget(no_button)

        self.popup = Popup(title='Move Barcode?', content=popup_content, size_hint=(0.75, 0.4))
        self.popup.open()

    def move_barcode(self, barcode, found_in_location):
        """Moves the barcode from its previous location to the current one."""
        # Remove the barcode from the previous location
        if barcode in location_dict[found_in_location]:
            location_dict[found_in_location].remove(barcode)
            if not location_dict[found_in_location]:  # Remove the location if no barcodes are left
                del location_dict[found_in_location]

        # Check if the barcode already exists in the new location to avoid adding it twice
        if self.current_location not in location_dict:
            location_dict[self.current_location] = []

        if barcode not in location_dict[self.current_location]:
            location_dict[self.current_location].append(barcode)

        self.label.text = f"Barcode {barcode} moved to {self.current_location}."
        self.success_sound.play()

        self.text_input.text = ""  # Clear the input
        self.save_location_data()

        # Ensure the popup is dismissed after the barcode is moved
        if hasattr(self, 'popup'):
            self.popup.dismiss()

    def find_barcode(self, instance):
        barcode = self.text_input.text.strip()  # Strip any extra spaces or newline characters
        self.text_input.text = ""  # Clear the input field after searching
        self.adding_to_location = False  # Switch to search mode

        if not barcode:
            self.label.text = "Please enter or scan a barcode."
            return

        # Ensure the barcode and stored barcodes are strings (in case of type issues)
        barcode = str(barcode)

        # Check if barcode exists in any location
        found_in_location = None
        for location, barcodes in location_dict.items():
            barcodes = [str(b) for b in barcodes]  # Convert all barcodes to strings
            if barcode in barcodes:
                found_in_location = location
                break

        if found_in_location:
            self.label.text = f"Barcode {barcode} is in {found_in_location}."
            self.success_sound.play()
        else:
            self.label.text = f"Barcode {barcode} not found."
            self.error_sound.play()

    def save_location_data(self):
        """Saves the location_dict to a JSON file."""
        try:
            with open(LOCATION_FILE, 'w') as f:
                json.dump(location_dict, f)
        except Exception as e:
            self.label.text = f"Error saving data: {e}"

    def load_location_data(self):
        """Loads location data from a JSON file."""
        global location_dict
        try:
            with open(LOCATION_FILE, 'r') as f:
                location_dict = json.load(f)
        except FileNotFoundError:
            location_dict = {}
        except Exception as e:
            self.label.text = f"Error loading data: {e}"

if __name__ == '__main__':
    CameraApp().run()
