import json
import os
import google.generativeai as genai
import tkinter as tk
from tkinter import simpledialog

# Scaling factor to convert feet to pixels (1 ft = 5 pixels)
SCALE = 5

def get_layout_from_gemini(total_width, total_height, rooms):
    """
    Interacts with Gemini API to generate a floor plan layout and door locations.

    Args:
        total_width (int): Total width of the layout area in feet.
        total_height (int): Total height of the layout area in feet.
        rooms (list): List of dictionaries containing room details (name, width, height).

    Returns:
        layout: List of dictionaries with room coordinates (room_name, x_start, y_start, width, height).
        doors: List of strings specifying door locations between rooms.
    """

    # Prepare room details for the prompt
    room_details = "\n".join([f"{i}. {room['name']}: {room['width']} ft width, {room['height']} ft height" 
                              for i, room in enumerate(rooms, start=1)])

    # Optimized prompt for generating the layout
    prompt = f"""
    Generate a floor plan layout within a {total_width}x{total_height} feet area that includes the following rooms:
    {room_details}

    Important constraints for door placements:
    1. Ensure a door between the bedrooms and the toilets (bathrooms) and toilets should have only one door.
    2. Ensure a door between the dining hall and the kitchen.
    3. The hall should connect to any adjacent rooms that currently do not have doors, except for rooms already connected by doors.
    4. Place doors logically between any adjacent rooms, ensuring proper connectivity.
    5. Ensure every rooms connected to another room through doors [IMPORTANT!!!]

    I need the output in a JSON format that includes:
    - A 'layout' key containing a list of rooms with:
      - room_name: the name of the room,
      - x_start: the x-coordinate for the room's top-left corner (in feet),
      - y_start: the y-coordinate for the room's top-left corner (in feet),
      - width: the room's width (in feet),
      - height: the room's height (in feet).
    - A 'doors' key that contains a list of door connections. Each entry should specify the two rooms connected by a door, using the format: "Room1-Room2".

    Ensure the layout fits within the specified area dimensions and satisfies the door placement constraints.
    Make sure the layout fits within the total area dimensions, and return only the JSON output as described.
    """
    
    # Gemini API interaction code remains the same
    genai.configure(api_key="#Ur API Key here")

    generation_config = {
        "temperature": 1,
        "top_p": 0.95,
        "top_k": 64,
        "max_output_tokens": 8192,
        "response_mime_type": "text/plain",
    }

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        generation_config=generation_config,
    )

    chat_session = model.start_chat()
    response = chat_session.send_message(prompt)

    print("Response Object:", response)

    try:
        raw_response = response._result.candidates[0].content.parts[0].text.strip()

        # Clean response and parse as JSON
        clean_response = raw_response.strip('```json').strip()
        print("Cleaned Response:", repr(clean_response))

        # Parse the JSON response
        response_data = json.loads(clean_response)
        layout = response_data.get("layout")
        doors = response_data.get("doors", [])

        return layout, doors

    except json.JSONDecodeError as e:
        print(f"Error while parsing response: {e}")
        raise ValueError("Invalid format received from the API")
    except IndexError as e:
        print(f"Error accessing response content: {e}")
        raise ValueError("Invalid response structure received from the API")
    except AttributeError as e:
        print(f"Error accessing response: {e}")
        raise ValueError("Unexpected response structure")

class BlueprintApp:
    def __init__(self, root, layout, doors, total_width, total_height):
        self.root = root
        self.root.title("2D House Blueprint Generator")
        global SCALE
        SCALE = 20  # Increase SCALE for larger room sizes
        canvas_width = total_width * SCALE
        canvas_height = total_height * SCALE
        self.canvas = tk.Canvas(self.root, bg="white")
        self.canvas.pack(expand=True, fill=tk.BOTH)
        self.root.after(100, self.center_layout, layout, doors, canvas_width, canvas_height)

    def center_layout(self, layout, doors, canvas_width, canvas_height):
        self.canvas.update_idletasks()
        current_canvas_width = self.canvas.winfo_width()
        current_canvas_height = self.canvas.winfo_height()
        x_offset = max(0, (current_canvas_width - canvas_width) // 2)
        y_offset = max(0, (current_canvas_height - canvas_height) // 2)
        room_rects = {}

        for room in layout:
            room_rects[room["room_name"]] = self.create_room(
                room["room_name"], room["x_start"], room["y_start"], room["width"], room["height"], x_offset, y_offset
            )

        for door in doors:
            room1, room2 = door.split("-")
            self.place_door_between_rooms(room_rects[room1], room_rects[room2])

    def create_room(self, name, x, y, width, height, x_offset, y_offset):
        x *= SCALE
        y *= SCALE
        width *= SCALE
        height *= SCALE

        x += x_offset
        y += y_offset

        # Draw the room as a rectangle
        rect = self.canvas.create_rectangle(x, y, x + width, y + height, fill="lightblue", tags=name)

        # Add room label (centered text)
        room_text = f"{name}\n{width // SCALE}x{height // SCALE} ft"
        text_id = self.canvas.create_text(x + width // 2, y + height // 2, text=room_text, fill="black")

        # Bind the room to be draggable
        self.make_draggable(rect, text_id)

        return (x, y, width, height)

    def place_door_between_rooms(self, room1_coords, room2_coords):
        x1, y1, width1, height1 = room1_coords
        x2, y2, width2, height2 = room2_coords

        door_rect = None  # Initialize door_rect to None

        # Adjust logic for placing doors at shared boundaries between adjacent rooms
        if x1 + width1 == x2 or x2 + width2 == x1:
            # Rooms are adjacent on the vertical side (left-right adjacency)
            x_door = (x1 + x2 + width1) // 2
            y_door = (max(y1, y2) + min(y1 + height1, y2 + height2)) // 2
            door_width, door_height = SCALE // 4, SCALE  # Vertical door
            door_rect = self.canvas.create_rectangle(x_door, y_door, x_door + door_width, y_door + door_height, fill="red", tags="door")
            
        elif y1 + height1 == y2 or y2 + height2 == y1:
            # Rooms are adjacent on the horizontal side (top-bottom adjacency)
            x_door = (max(x1, x2) + min(x1 + width1, x2 + width2)) // 2
            y_door = (y1 + y2 + height1) // 2
            door_width, door_height = SCALE, SCALE // 4  # Horizontal door
            door_rect = self.canvas.create_rectangle(x_door, y_door, x_door + door_width, y_door + door_height, fill="red", tags="door")

        # Only make the door draggable if door_rect is created
        if door_rect is not None:
            self.make_draggable(door_rect, None)


    def make_draggable(self, item_id, text_id=None):
        def on_drag_start(event):
            # Save the initial position when clicking on the room/door
            self.canvas.bind("<B1-Motion>", on_drag_motion)
            self.canvas.bind("<ButtonRelease-1>", on_drag_release)
            self.canvas.start_x = event.x
            self.canvas.start_y = event.y

        def on_drag_motion(event):
            # Calculate the distance moved
            dx = event.x - self.canvas.start_x
            dy = event.y - self.canvas.start_y

            # Move the selected item (room/door) and associated text if applicable
            self.canvas.move(item_id, dx, dy)
            if text_id:
                self.canvas.move(text_id, dx, dy)

            # Update the start positions for the next motion
            self.canvas.start_x = event.x
            self.canvas.start_y = event.y

        def on_drag_release(event):
            # Unbind the motion event after releasing the mouse
            self.canvas.unbind("<B1-Motion>")
            self.canvas.unbind("<ButtonRelease-1>")

        # Bind the mouse press and drag events to the specific item (room/door)
        self.canvas.tag_bind(item_id, "<ButtonPress-1>", on_drag_start)
        if text_id:
            self.canvas.tag_bind(text_id, "<ButtonPress-1>", on_drag_start)

def get_user_input():
    root = tk.Tk()
    root.withdraw()
    total_width = simpledialog.askinteger("Input", "Enter total width of layout (in feet):", minvalue=1)
    total_height = simpledialog.askinteger("Input", "Enter total height of layout (in feet):", minvalue=1)
    rooms = []

    while True:
        room_name = simpledialog.askstring("Input", "Enter room name (or type 'done' to finish):")
        if room_name.lower() == "done":
            break
        room_width = simpledialog.askinteger("Input", f"Enter width of {room_name} (in feet):", minvalue=1)
        room_height = simpledialog.askinteger("Input", f"Enter height of {room_name} (in feet):", minvalue=1)
        rooms.append({"name": room_name, "width": room_width, "height": room_height})

    return total_width, total_height, rooms

if __name__ == "__main__":
    total_width, total_height, rooms = get_user_input()
    layout, doors = get_layout_from_gemini(total_width, total_height, rooms)
    root = tk.Tk()
    app = BlueprintApp(root, layout, doors, total_width, total_height)
    root.mainloop()
