from datetime import datetime
from flask import request
from pymongo import MongoClient, ASCENDING, DESCENDING
import os
import qrcode
from PIL import Image, ImageDraw, ImageFont
from escpos.printer import Usb
from bson import ObjectId  # Import ObjectId from bson
from bson.regex import Regex
import pytz
from collection_format import Session, User, GateEntry

# MongoDB connection setup
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://shiven:shiven424@cluster0.x0f38.mongodb.net/")
client = MongoClient(MONGO_URI)

# Database and collection
db = client.cllg_gate
gate_entries = db.gate_entries
users = db.users
sessions = db.sessions

# Directory to store QR codes
QR_CODES_DIR = "static/qr_codes"
os.makedirs(QR_CODES_DIR, exist_ok=True)

# Function to convert MongoDB ObjectId to string for JSON serialization
def object_id_to_str(entry):
    if isinstance(entry, ObjectId):
        return str(entry)
    if isinstance(entry, dict):
        return {key: object_id_to_str(value) for key, value in entry.items()}
    if isinstance(entry, list):
        return [object_id_to_str(item) for item in entry]
    return entry

def create_user(username, password, role, shift=None):
    existing_user = users.find_one({"username": username})
    if not existing_user:
        user = User(username=username, password=password, role=role, shift=shift)
        users.insert_one(user.to_dict())
        return True
    print("User already exists")
    return False

def authenticate_user(username, password):
    """Authenticate a user by checking username and password."""
    user = users.find_one({"username": username})
    if user and user["password"] == password:
        return {"username": user["username"], "role": user["role"]}
    return None

def start_session(username, ip_address, session_id):
    try:
        # Get current time in Asia/Kolkata timezone
        ist = pytz.timezone('Asia/Kolkata')
        session_login_time = datetime.now(ist).strftime('%d-%m-%Y %a %H:%M:%S')  # Custom format as string

        # Create session data
        session_data = {
            "username": username,
            "password": "",  # Password is not stored for session tracking
            "session_login_time": session_login_time,
            "session_logout_time": None,
            "ip_address": ip_address,
            "session_id": session_id,
        }

        # Insert the session into the database
        sessions.insert_one(session_data)
        return True
    except Exception as e:
        print(f"Error starting session for user '{username}': {e}")
        return False

def end_session(username, session_id):
    try:
        # Use Asia/Kolkata timezone for consistency
        ist = pytz.timezone('Asia/Kolkata')
        session_logout_time = datetime.now(ist).strftime('%d-%m-%Y %a %H:%M:%S')  # Custom format as string

        # Update the session with the logout time
        result = sessions.update_one(
            {"username": username, "session_id": session_id, "session_logout_time": None},  # Find active session
            {"$set": {"session_logout_time": session_logout_time}}  # Set logout time in custom format
        )
        return result.matched_count > 0
    except Exception as e:
        print(f"Error ending session for user '{username}': {e}")
        return False

def generate_entry_id():
    today = datetime.now()
    date_prefix = today.strftime("%Y%m%d")  # Format: YYYYMMDD
    daily_count = gate_entries.count_documents({"entry_id": {"$regex": f"^{date_prefix}"}})
    entry_id = f"{date_prefix}{str(daily_count + 1).zfill(4)}"  # YYYYMMDD + daily_count
    return entry_id

def create_gate_entry(data):
    # Generate the base entry data
    entry_id = generate_entry_id()
    ist = pytz.timezone('Asia/Kolkata')
    in_time_ist = datetime.now(ist)
    # print(in_time_ist)
    gate_entry = GateEntry(
        entry_id=entry_id,
        name=data["name"],
        contact_no=data["contact_no"],
        destination=data["destination"],
        reason=data["reason"],
        in_time=in_time_ist,
        vehicle_type=data.get("vehicle_type", "none"),
        vehicle_no=data.get("vehicle_no", None),
        out_time=None,
        no_driver=data.get("no_driver", 0),
        no_student=data.get("no_student", 0),
        no_visitor=data.get("no_visitor", 0),
        remarks=data.get("remarks", None)
    )

    gate_entry.update_no_person()    
    entry_data = gate_entry.to_dict()    
    gate_entries.insert_one(entry_data)    
    return gate_entry.entry_id

def mark_exit_by_id(entry_id, out_time):
    result = gate_entries.update_one(
        {"entry_id": entry_id, "out_time": None},
        {"$set": {"out_time": out_time}}
    )
    return result.matched_count > 0

def add_remark_wrong_entry(entry_id):
    """
    Appends 'WRONG_ENTRY' to the 'remarks' field of the entry with the given entry_id.
    """
    try:
        # Fetch the existing entry
        entry = gate_entries.find_one({"entry_id": entry_id})
        if not entry:
            return False  # No matching entry found

        # Update the remarks field by appending 'WRONG_ENTRY'
        existing_remarks = entry.get("remarks", "")
        updated_remarks = f"{existing_remarks} WRONG_ENTRY".strip()
        gate_entries.update_one(
            {"entry_id": entry_id},
            {"$set": {"remarks": updated_remarks}}
        )
        return True
    except Exception as e:
        print(f"Error updating remarks: {e}")
        return False

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

def fetch_all_entries(page, limit):
    # Calculate the number of documents to skip for pagination
    skip = (page - 1) * limit
    
    # Fetch paginated entries from the database and sort by "in_time" in descending order
    entries_cursor = gate_entries.find().sort("in_time", -1).skip(skip).limit(limit)
    total_entries = gate_entries.count_documents({})  # Get the total number of entries
    
    # Convert ObjectId to string for each entry
    entries = [object_id_to_str(entry) for entry in entries_cursor]
    
    return entries, total_entries

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

def search_visitor_by_contact(contact_no, page, limit):
    """Searches for visitors by contact number with pagination."""
    try:
        query = {"contact_no": {"$regex": contact_no, "$options": "i"}}  # Case-insensitive search
        return _execute_query_with_pagination(query, page, limit)
    except Exception as e:
        print(f"Error in search_visitor_by_contact: {e}")
        return [], 0

def search_visitor_by_id(entry_id, page, limit):
    """Searches for a visitor by entry ID (ObjectId) with pagination."""
    try:
        query = {"entry_id": {"$regex": entry_id, "$options": "i"}}  # Case-insensitive search for ID
        return _execute_query_with_pagination(query, page, limit)
    except Exception as e:
        print(f"Error in search_visitor_by_id: {e}")
        return [], 0

def search_visitor_by_name(name, page, limit):
    """Searches for visitors by name with pagination."""
    try:
        query = {"name": {"$regex": name, "$options": "i"}}  # Case-insensitive partial match
        return _execute_query_with_pagination(query, page, limit)
    except Exception as e:
        print(f"Error in search_visitor_by_name: {e}")
        return [], 0

def search_visitor_by_date(date_string, page, limit):
    """Searches for visitors by a specific date with pagination."""
    try:
        parsed_date = datetime.strptime(date_string, "%d/%m/%Y").strftime("%d-%m-%Y")
        # Query to match the date in the "in_time" field
        query = {"in_time": {"$regex": f"^{parsed_date}", "$options": "i"}}  # Case-insensitive match at the start of the string
        return _execute_query_with_pagination(query, page, limit)
    except Exception as e:
        print(f"Error in search_visitor_by_date: {e}")
        return [], 0
    
def _execute_query_with_pagination(query, page, limit):
    """Executes a MongoDB query with pagination and formats the results for JSON compatibility."""
    try:
        # Calculate the number of documents to skip based on the page and limit
        skip = (page - 1) * limit

        # Fetch results with pagination
        total_entries = gate_entries.count_documents(query)  # Total number of matching documents
        results = list(
            gate_entries.find(query)
            .sort("in_time", -1)
            .skip(skip)
            .limit(limit)
        )

        # Format results for JSON compatibility
        formatted_results = []
        for result in results:
            formatted_result = {
                "entry_id": result.get("entry_id", "N/A"),
                "name": result.get("name", "N/A"),
                "contact_no": result.get("contact_no", "N/A"),
                "vehicle_no": result.get("vehicle_no", "N/A"),
                "destination": result.get("destination", "N/A"),
                "reason": result.get("reason", "N/A"),
                "in_time": result.get("in_time", "N/A"),
                "vehicle_type": result.get("vehicle_type", "N/A"),
                "remarks": result.get("remarks", "N/A"),
                "out_time": result.get("out_time", "N/A"),
            }
            formatted_results.append(formatted_result)

        return formatted_results, total_entries
    except Exception as e:
        print(f"Error executing query with pagination: {e}")
        return [], 0

def search_inside_visitor_by_contact(contact_no):
    """Searches for visitors by contact number who are currently inside."""
    query = {"contact_no": contact_no, "out_time": None}
    return _inside_execute_query(query)

def search_inside_visitor_by_id(entry_id):
    """Searches for a visitor by entry ID (ObjectId) who is currently inside."""
    try:
        query = {"entry_id": entry_id, "out_time": None}
    except Exception as e:
        print(f"Invalid ID format: {e}")
        return []
    return _inside_execute_query(query)

def search_inside_visitor_by_name(name):
    """Searches for visitors by name who are currently inside."""
    query = {"name": name, "out_time": None}
    return _inside_execute_query(query)

def search_inside_visitor_by_date(date_string):
    """Searches for visitors by a specific date with pagination."""
    try:
        parsed_date = datetime.strptime(date_string, "%d/%m/%Y").strftime("%d-%m-%Y")
        # Query to match the date in the "in_time" field
        query = {"in_time": {"$regex": f"^{parsed_date}", "$options": "i"}, "out_time": None}  # Case-insensitive match at the start of the string
        return _inside_execute_query(query)
    except Exception as e:
        print(f"Error in search_visitor_by_date: {e}")
        return [], 0
    
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
                    "in_time": 1,  # Fetch in_time to derive entry date
                    "vehicle_no": 1
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
    
def get_guards():
    try:
        guards = list(users.find({"role": "guard"}, {"_id": 0, "username": 1}))
        print(guards)
        return [guard["username"] for guard in guards]
    except Exception as e:
        print(f"Error fetching guards for shift : {e}")
        return []

def get_all_sessions_guards():
    try:
        # Query all session records
        sessions_data = list(sessions.find({"username": {"$ne": "admin"}}, {"_id": 0}).sort("session_login_time", DESCENDING))
        return sessions_data
    except Exception as e:
        print(f"Error fetching sessions: {e}")
        return []

def reset_password(username, new_password):
    try:
        # Find the user and update the password
        result = users.update_one(
            {"username": username},  # Find user by username
            {"$set": {"password": new_password}}  # Set the new hashed password
        )
        
        if result.matched_count > 0:
            return True
        else:
            print(f"User '{username}' not found.")
            return False
    except Exception as e:
        print(f"Error resetting password for user '{username}': {e}")
        return False

def get_old_password(username):
    try:
        # Find the user by username and fetch the password
        user = users.find_one({"username": username}, {"_id": 0, "password": 1})
        if user:
            return user.get("password")
        else:
            print(f"User '{username}' not found.")
            return None
    except Exception as e:
        print(f"Error fetching old password for user '{username}': {e}")
        return None

def get_admins():
    try:
        # Query the sessions collection for admins
        admins = list(users.find({"role": "admin"}, {"_id": 0, "username": 1}))
        return [admin["username"] for admin in admins]
    except Exception as e:
        print(f"Error fetching admins: {e}")
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

    create_user("guard1", "pass", "guard", shift="morning")
    create_user("guard2", "pass", "guard", shift="evening")
    create_user("guard3", "pass", "guard", shift="night")
    create_user("admin", "pass", "admin")
    

    # all_entries = fetch_all_entries()
    # for entry in all_entries:
    #     print(entry)
