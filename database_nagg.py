from datetime import datetime
from pymongo import MongoClient
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Usb
from bson import ObjectId  # Import ObjectId from bson
from bson.regex import Regex

# MongoDB connection setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://naggender2:11nsr11@cluster0.5yi5h.mongodb.net/")
client = MongoClient(MONGO_URI)

# Database and collection
db = client.cllg_gate
gate_entries = db.gate_entries

# Directory to store QR codes
QR_CODES_DIR = "static/qr_codes"
os.makedirs(QR_CODES_DIR, exist_ok=True)

# Function to convert MongoDB ObjectId to string for JSON serialization

# def fetch_last_five_entries(contact_no):
#     """
#     Fetch the last five entries for a given contact number.
#     """
#     try:
#         # Query MongoDB to find the last five entries for the contact number
#         entries = list(
#             gate_entries.find(
#                 {"contact_no": contact_no},  # Filter by contact number
#                 {"_id": 0, "entry_id": 1, "destination": 1, "reason": 1, "vehicle_type": 1, "in_time": 1}  # Fields to return
#             )
#             .sort("in_time", -1)  # Sort by in_time in descending order
#             .limit(5)  # Limit the results to 5
#         )

#         return entries  # Return the formatted results

#     except Exception as e:
#         print(f"Error fetching last five entries: {e}")
#         return []

def fetch_last_five_entries(contact_no):
    """
    Fetch the last five entries for a given contact number, including the formatted entry date.
    """
    try:
        # Query MongoDB to find the last five entries for the contact number
        entries = list(
            gate_entries.find(
                {"contact_no": contact_no},  # Filter by contact number
                {
                    "_id": 0,  # Exclude the MongoDB ObjectId
                    "entry_id": 1,
                    "destination": 1,
                    "reason": 1,
                    "vehicle_type": 1,
                    "in_time": 1,
                    "vehicle_no": 1  # Fetch in_time to derive entry date
                }
            )
            .sort("in_time", -1)  # Sort by in_time in descending order
            .limit(3)  # Limit the results to 5
        )

        # Format the results to include a human-readable entry date
        for entry in entries:
            # Extract date from in_time and format it as 'DD-MM-YYYY'
            entry_datetime = entry["in_time"]
            entry["entry_date"] = entry_datetime.strftime("%d-%m-%Y") if isinstance(entry_datetime, datetime) else "N/A"

        return entries  # Return the formatted results

    except Exception as e:
        print(f"Error fetching last five entries: {e}")
        return []


def object_id_to_str(entry):
    if isinstance(entry, ObjectId):
        return str(entry)
    if isinstance(entry, dict):
        return {key: object_id_to_str(value) for key, value in entry.items()}
    if isinstance(entry, list):
        return [object_id_to_str(item) for item in entry]
    return entry

def generate_entry_id():
    today = datetime.now()
    date_prefix = today.strftime("%Y%m%d")  # Format: YYYYMMDD
    daily_count = gate_entries.count_documents({"entry_id": {"$regex": f"^{date_prefix}"}})
    entry_id = f"{date_prefix}{str(daily_count + 1).zfill(4)}"  # YYYYMMDD + daily_count
    return entry_id

def create_gate_entry(data):
    # Generate the base entry data
    entry_data = {
        "entry_id": generate_entry_id(),
        "name": data["name"],
        "contact_no": data["contact_no"],
        "destination": data["destination"],
        "reason": data["reason"],
        "in_time": datetime.now(),
        "out_time": None,
        "remarks": data["remarks"]
    }

    # Add vehicle_no if provided
    if "vehicle_no" in data and data["vehicle_no"]:
        entry_data["vehicle_no"] = data["vehicle_no"]

    # Add vehicle_type if provided
    if "vehicle_type" in data and data["vehicle_type"]:
        entry_data["vehicle_type"] = data["vehicle_type"]

    gate_entries.insert_one(entry_data)
    return entry_data["entry_id"]

def mark_exit_by_id(entry_id, out_time):
    result = gate_entries.update_one(
        {"entry_id": entry_id, "out_time": None},
        {"$set": {"out_time": out_time}}
    )
    return result.matched_count > 0

def mark_exit_by_vehicle(vehicle_no, out_time):
    result = gate_entries.find_one_and_update(
        {"vehicle_no": vehicle_no, "out_time": None},
        {"$set": {"out_time": out_time}},
        sort=[("in_time", -1)]  # Sort by in_time in descending order
    )
    return result is not None  # Return True if a document was found and updated, else False


def mark_exit_by_contact(contact_no, out_time):
    # Find the most recent entry for the given contact_no with out_time as None
    result = gate_entries.find_one_and_update(
        {"contact_no": contact_no, "out_time": None},
        {"$set": {"out_time": out_time}},
        sort=[("in_time", -1)]  # Sort by in_time in descending order
    )
    # Return True if a document was updated, otherwise False
    return result is not None


def mark_exit_by_qr_code(entry_id, out_time):
    # Check for the entry with the provided entry_id and mark exit if the entry exists
    result = gate_entries.update_one(
        {"entry_id": entry_id, "out_time": None},
        {"$set": {"out_time": out_time}}
    )
    return result.matched_count > 0

def fetch_all_entries():
    # Fetch all entries and convert ObjectId to string
    entries = list(gate_entries.find().sort("in_time", -1))  # Retrieves all entries in the gate_entries collection
    # Convert ObjectId to string for each entry
    return [object_id_to_str(entry) for entry in entries]

def fetch_entries_with_blank_out_time():
    # Fetch only those entries where 'out_time' is None (blank)
    entries = list(gate_entries.find({"out_time": None}).sort("in_time", -1))  # Filter on out_time being None
    return [object_id_to_str(entry) for entry in entries]

def generate_qr_code(entry_id):
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(entry_id)
    qr.make(fit=True)
    qr_image = qr.make_image(fill="black", back_color="white")
    qr_image = qr_image.resize((100, 100))  # Resize QR code to fit on slip
    return qr_image

def get_visitor_details_by_mobile(contact_no):
    # Find the most recent entry with the provided mobile number
    entry = gate_entries.find_one(
        {"contact_no": contact_no},
        {"name": 1, "vehicle_no": 1, "vehicle_type": 1},
        sort=[("in_time", -1)]  # Sort by in_time in descending order to get the latest
    )
    if entry:
        return {
            "name": entry.get("name"),
            "vehicle_no": entry.get("vehicle_no", ""),
            "vehicle_type": entry.get("vehicle_type", "")
        }
    return None


# def search_entries(search_type, query):
#     # Build the query filter based on search_type
#     if search_type == "ID":
#         filter_criteria = {"entry_id": Regex(f".*{query}.*", "i")}
#     elif search_type == "Name":
#         filter_criteria = {"name": Regex(f".*{query}.*", "i")}
#     elif search_type == "Mobile Number":
#         filter_criteria = {"contact_no": Regex(f".*{query}.*", "i")}
#     else:
#         raise ValueError("Invalid search type")

#     # Execute the search query on the database
#     matching_entries = gate_entries.find(filter_criteria)
#     return [object_id_to_str(entry) for entry in matching_entries]

def search_visitor_by_contact(contact_no):
    """Searches for visitors by contact number."""
    query = {"contact_no": contact_no}
    return _execute_query(query)

def search_visitor_by_id(entry_id):
    """Searches for a visitor by entry ID (ObjectId)."""
    try:
        query = {"entry_id": entry_id}
    except Exception as e:
        print(f"Invalid ID format: {e}")
        return []
    return _execute_query(query)

def search_visitor_by_name(name):
    """Searches for visitors by name."""
    query = {"name": name}
    return _execute_query(query)

def _execute_query(query):
    """Executes a MongoDB query and formats the results for JSON compatibility."""
    try:
        results = list(gate_entries.find(query))
        for result in results:
            result["entry_id"] = result["entry_id"]
            del result["_id"]
        return results
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def search_inside_visitor_by_contact(contact_no):
    """Searches for visitors by contact number who are currently inside."""
    query = {"contact_no": contact_no, "out_time": None}
    return _execute_query(query)

def search_inside_visitor_by_id(entry_id):
    """Searches for a visitor by entry ID (ObjectId) who is currently inside."""
    try:
        query = {"entry_id": entry_id, "out_time": None}
    except Exception as e:
        print(f"Invalid ID format: {e}")
        return []
    return _execute_query(query)

def search_inside_visitor_by_name(name):
    """Searches for visitors by name who are currently inside."""
    query = {"name": name, "out_time": None}
    return _inside_execute_query(query)

def _inside_execute_query(query):
    """Executes a MongoDB query and formats the results for JSON compatibility."""
    try:
        results = list(gate_entries.find(query))
        for result in results:
            result["entry_id"] = str(result["entry_id"])  # Convert ObjectId to string for JSON compatibility
            del result["_id"]  # Remove internal MongoDB ID
        return results
    except Exception as e:
        print(f"Error executing query: {e}")
        return []

def generate_slip(entry_data):
    # Generate the QR code image
    qr_image = generate_qr_code(entry_data['entry_id'])

    # Create a new image with the necessary space for the QR code and text
    slip_width = 384  # Standard width for thermal printers
    slip_height = 480  # Adjust height as needed
    slip_image = Image.new('1', (slip_width, slip_height), color=255)  # 1-bit image (black and white)
    draw = ImageDraw.Draw(slip_image)

    # Fonts setup
    try:
        font_header = ImageFont.truetype("arialbd.ttf", 20)  # Bold font for header
        font_body = ImageFont.truetype("arial.ttf", 16)  # Regular font for body text
    except IOError:
        font_header = ImageFont.load_default()  # Fallback to default font if custom font is not available
        font_body = ImageFont.load_default()  # Fallback to default font for body

    # Add "BITS ENTRY-EXIT PASS" header with black background and white text
    header_text = "BITS ENTRY-EXIT PASS"
    header_height = 40
    draw.rectangle([(0, 0), (slip_width, header_height)], fill=0)  # Draw black rectangle for header

    # Using textbbox to get text size for center alignment
    bbox = draw.textbbox((0, 0), header_text, font=font_header)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    
    # Center the header text within the header area
    draw.text(((slip_width - text_width) / 2, (header_height - text_height) / 2),
              header_text, font=font_header, fill=255)

    # Add other details to the slip with padding and alignment
    text_y_offset = header_height + 15  # Starting position for text after header
    details = [
        ("ID", entry_data['entry_id']),
        ("Name", entry_data['name']),
        ("Contact No.", entry_data['contact_no']),
        ("Destination", entry_data['destination']),
        ("Reason", entry_data['reason']),
        ("Remarks", entry_data['remarks'])
    ]

    # Draw body text in box with padding
    line_height = 20
    box_x_start = 10
    box_x_end = slip_width - 10

    # Draw a box around the details
    box_y_start = text_y_offset - 5
    for label, value in details:
        text_line = f"{label}: {value}"
        draw.text((box_x_start + 10, text_y_offset), text_line, font=font_body, fill=0)
        text_y_offset += line_height
    box_y_end = text_y_offset + 5
    draw.rectangle([box_x_start, box_y_start, box_x_end, box_y_end], outline=0, width=2)

    # Separator line before the QR code
    text_y_offset += 15
    draw.line((10, text_y_offset, slip_width - 10, text_y_offset), fill=0, width=2)
    text_y_offset += 10

    # Center and paste QR code image at the bottom of the slip
    qr_code_x_pos = (slip_width - qr_image.width) // 2
    slip_image.paste(qr_image, (qr_code_x_pos, text_y_offset))

    return slip_image

# Function to print the slip using thermal printer
def print_slip(entry_data):
    # Generate the slip image with the QR and details
    slip_image = generate_slip(entry_data)

    # Preview the generated slip before printing
    slip_image.show()  # This will open the image in your default image viewer

    # Connect to the thermal printer (adjust the parameters as needed for your printer)
    # printer = Usb(0x04b8, 0x0202)  # Replace with your USB printer's vendor and product ID
    # Convert the slip image to byte data (escpos compatible format)
    # img_byte_array = io.BytesIO()
    # slip_image.save(img_byte_array, format='PNG')
    # img_byte_array.seek(0)

    # Send the image to the printer
    # printer.image(img_byte_array)
    # printer.cut()  # Cut the paper after printing

# Example usage
if __name__ == "__main__":
    # Uncomment the following lines if you want to test the functions
    # example_entry_data = {
    #     "name": "John Doe",
    #     "contact_no": "1234567890",
    #     "vehicle_no": "AB-1234",  # Optional, include only if the person has a vehicle
    #     "vehicle_type": "car",  # Optional, include only if the person has a vehicle
    #     "destination": "Library",
    #     "reason": "Research work",
    #     "remarks": "N/A"
    # }
    # entry_id = create_gate_entry(example_entry_data)
    # print("Entry created with ID:", entry_id)

    
# Example entry data
    entry_data = {
        "entry_id": "202311090001",  # Entry ID that will be embedded in the QR code
        "name": "John Doe",
        "contact_no": "1234567890",
        "destination": "Library",
        "reason": "Research work",
        "remarks": "N/A"
    }

    # Print the slip and preview it
    print_slip(entry_data)

    # all_entries = fetch_all_entries()
    # for entry in all_entries:
    #     print(entry)
