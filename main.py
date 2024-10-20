import json
import os
from kivy.app import App
from kivy.uix.button import Button
from kivy.uix.popup import Popup
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.image import Image
from kivy.graphics.texture import Texture
from kivy.clock import Clock
from pyzbar.pyzbar import decode
import cv2
import numpy as np

# Define the path for the JSON file
JSON_FILE = 'inventory_data.json'


class CameraApp(App):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical')
        self.image_display = Image(size_hint=(1, 1))
        self.capture = cv2.VideoCapture(0)
        self.data = self.load_json()
        self.select_location_button = Button(text="Select Location/Shelf", size_hint=(0.3, 0.1))
        self.current_shelf_path = []
        self.popup = None
        self.create_location_popup = None
        self.shelf_popup = None
        self.new_location_input = None
        self.new_shelf_input = None
        self.create_shelf_popup = None
        self.nested_shelf_popup = None
        self.create_nested_shelf_popup = None
        self.new_nested_shelf_input = None

    def build(self):
        self.layout = BoxLayout(orientation='vertical')
        self.image_display = Image(size_hint=(1, 1))
        self.layout.add_widget(self.image_display)

        self.capture = cv2.VideoCapture(0)
        Clock.schedule_interval(self.update, 1.0 / 30.0)

        # Create or load the JSON file
        self.data = self.load_json()

        # Add button for selecting location and shelf
        self.select_location_button = Button(text="Select Location/Shelf", size_hint=(0.3, 0.1))
        self.select_location_button.bind(on_press=self.open_location_popup)
        self.layout.add_widget(self.select_location_button)

        return self.layout  # The root widget is returned from here

    def update(self, dt):
        ret, frame = self.capture.read()
        if ret:
            decoded_objects = decode(frame)
            for obj in decoded_objects:
                barcode_data = obj.data.decode('utf-8')
                points = obj.polygon
                if len(points) == 4:
                    pts = np.array(points, dtype=np.int32)
                else:
                    pts = cv2.convexHull(np.array([point for point in points], dtype=np.int32))
                cv2.polylines(frame, [pts], True, (0, 255, 0), 2)

                # Once a barcode is detected, store it in the current shelf
                self.store_barcode(barcode_data)

            buffer = cv2.flip(frame, 0).tobytes()
            texture = Texture.create(size=(frame.shape[1], frame.shape[0]), colorfmt='bgr')
            texture.blit_buffer(buffer, colorfmt='bgr', bufferfmt='ubyte')
            self.image_display.texture = texture

    def on_stop(self):
        if self.capture.isOpened():
            self.capture.release()

    @staticmethod
    def load_json():
        # Check if the JSON file exists, create one if not
        if not os.path.exists(JSON_FILE):
            data = {"locations": {}}
            with open(JSON_FILE, 'w') as file:
                json.dump(data, file)
            return data
        else:
            with open(JSON_FILE, 'r') as file:
                return json.load(file)

    def save_json(self):
        # Save the data back to the JSON file
        with open(JSON_FILE, 'w') as file:
            json.dump(self.data, file, indent=4)

    def store_barcode(self, barcode_data):
        # Store the barcode in the currently selected nested shelf
        if self.current_shelf_path:
            shelf = self.get_nested_shelf(self.current_shelf_path)
            if 'barcodes' not in shelf:
                shelf['barcodes'] = []
            shelf['barcodes'].append(barcode_data)
            self.save_json()
            print(f"Stored barcode: {barcode_data} in shelf: {' -> '.join(self.current_shelf_path)}")

    def get_nested_shelf(self, path):
        shelf = self.data['locations']
        for level in path:
            shelf = shelf['shelves'][level]
        return shelf

    def open_location_popup(self, instance):
        popup_layout = GridLayout(cols=2, padding=10, spacing=10)

        location_label = Label(text="Select or Create a Location:")
        popup_layout.add_widget(location_label)

        for location_name in self.data['locations']:
            button = Button(text=location_name, on_press=lambda btn, location=location_name: self.open_shelf_popup(location))
            popup_layout.add_widget(button)

        create_button = Button(text="Create New Location", on_press=self.create_location)
        popup_layout.add_widget(create_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        popup_layout.add_widget(close_button)

        self.popup = Popup(title="Select Location", content=popup_layout, size_hint=(0.8, 0.8))
        self.popup.open()

    def create_location(self):
        layout = BoxLayout(orientation='vertical')
        label = Label(text="Enter new location name:")
        layout.add_widget(label)

        self.new_location_input = TextInput(hint_text="Location Name", size_hint=(1, 0.2))
        layout.add_widget(self.new_location_input)

        create_button = Button(text="Create", on_press=self.confirm_location_creation)
        layout.add_widget(create_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        layout.add_widget(close_button)

        self.create_location_popup = Popup(title="New Location", content=layout, size_hint=(0.8, 0.8))
        self.create_location_popup.open()

    def confirm_location_creation(self):
        location_name = self.new_location_input.text.strip()
        if location_name and location_name not in self.data['locations']:
            self.data['locations'][location_name] = {"shelves": {}}
            self.save_json()

            self.create_location_popup.dismiss()
            self.open_shelf_popup(location_name)
        else:
            print("Invalid or duplicate location name.")

    def open_shelf_popup(self, location_name):
        popup_layout = GridLayout(cols=2, padding=10, spacing=10)
        label = Label(text=f"Location: {location_name}")
        popup_layout.add_widget(label)

        for shelf_name in self.data['locations'][location_name]['shelves']:
            button = Button(text=shelf_name, on_press=lambda btn, shelf=shelf_name: self.open_nested_shelf_popup(location_name, shelf))
            popup_layout.add_widget(button)

        create_shelf_button = Button(text="Create New Shelf", on_press=lambda btn: self.create_shelf(location_name))
        popup_layout.add_widget(create_shelf_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        popup_layout.add_widget(close_button)

        self.shelf_popup = Popup(title=f"Location: {location_name}", content=popup_layout, size_hint=(0.8, 0.8))
        self.shelf_popup.open()

    def create_shelf(self, location_name):
        layout = BoxLayout(orientation='vertical')
        label = Label(text="Enter new shelf name:")
        layout.add_widget(label)

        self.new_shelf_input = TextInput(hint_text="Shelf Name", size_hint=(1, 0.2))
        layout.add_widget(self.new_shelf_input)

        create_shelf_button = Button(text="Create Shelf", on_press=lambda btn: self.confirm_shelf_creation(location_name))
        layout.add_widget(create_shelf_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        layout.add_widget(close_button)

        self.create_shelf_popup = Popup(title="New Shelf", content=layout, size_hint=(0.8, 0.8))
        self.create_shelf_popup.open()

    def confirm_shelf_creation(self, location_name):
        shelf_name = self.new_shelf_input.text.strip()
        if shelf_name and shelf_name not in self.data['locations'][location_name]['shelves']:
            self.data['locations'][location_name]['shelves'][shelf_name] = {}
            self.save_json()
            self.create_shelf_popup.dismiss()
            self.open_nested_shelf_popup(location_name, shelf_name)
        else:
            print("Invalid or duplicate shelf name.")

    def open_nested_shelf_popup(self, location_name, parent_shelf):
        popup_layout = GridLayout(cols=2, padding=10, spacing=10)
        label = Label(text=f"Shelf: {parent_shelf}")
        popup_layout.add_widget(label)

        nested_shelves = self.data['locations'][location_name]['shelves'].get(parent_shelf, {})

        for nested_shelf in nested_shelves:
            button = Button(text=nested_shelf, on_press=lambda btn: self.select_nested_shelf(location_name, parent_shelf, nested_shelf))
            popup_layout.add_widget(button)

        create_nested_shelf_button = Button(text="Create New Nested Shelf", on_press=lambda btn: self.create_nested_shelf(location_name, parent_shelf))
        popup_layout.add_widget(create_nested_shelf_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        popup_layout.add_widget(close_button)

        self.nested_shelf_popup = Popup(title=f"Shelf: {parent_shelf}", content=popup_layout, size_hint=(0.8, 0.8))
        self.nested_shelf_popup.open()

    def select_nested_shelf(self, location_name, parent_shelf, nested_shelf):
        # Store the current shelf path to know where barcodes should go
        self.current_shelf_path = [location_name, parent_shelf, nested_shelf]
        print(f"Selected nested shelf: {' -> '.join(self.current_shelf_path)}")
        self.close_popup()  # Close all popups and start scanning

    def create_nested_shelf(self, location_name, parent_shelf):
        layout = BoxLayout(orientation='vertical')
        label = Label(text="Enter new nested shelf name:")
        layout.add_widget(label)

        self.new_nested_shelf_input = TextInput(hint_text="Nested Shelf Name", size_hint=(1, 0.2))
        layout.add_widget(self.new_nested_shelf_input)

        create_button = Button(text="Create Nested Shelf",
                               on_press=lambda btn: self.confirm_nested_shelf_creation(location_name, parent_shelf))
        layout.add_widget(create_button)

        close_button = Button(text="Close", on_press=self.close_popup)
        layout.add_widget(close_button)

        self.create_nested_shelf_popup = Popup(title="New Nested Shelf", content=layout, size_hint=(0.8, 0.8))
        self.create_nested_shelf_popup.open()

    def confirm_nested_shelf_creation(self, location_name, parent_shelf):
        nested_shelf_name = self.new_nested_shelf_input.text.strip()
        if nested_shelf_name and nested_shelf_name not in self.data['locations'][location_name]['shelves'][
            parent_shelf]:
            self.data['locations'][location_name]['shelves'][parent_shelf][nested_shelf_name] = {}
            self.save_json()
            self.create_nested_shelf_popup.dismiss()
            self.open_nested_shelf_popup(location_name, parent_shelf)
        else:
                print("Invalid or duplicate nested shelf name.")

    def close_popup(self):
            # Dismiss any open popup
        if hasattr(self, 'popup') and self.popup:
                self.popup.dismiss()
        if hasattr(self, 'create_location_popup') and self.create_location_popup:
                self.create_location_popup.dismiss()
        if hasattr(self, 'shelf_popup') and self.shelf_popup:
                self.shelf_popup.dismiss()
        if hasattr(self, 'create_shelf_popup') and self.create_shelf_popup:
                self.create_shelf_popup.dismiss()
        if hasattr(self, 'nested_shelf_popup') and self.nested_shelf_popup:
                self.nested_shelf_popup.dismiss()
        if hasattr(self, 'create_nested_shelf_popup') and self.create_nested_shelf_popup:
                self.create_nested_shelf_popup.dismiss()

if __name__ == '__main__':
    CameraApp().run()

