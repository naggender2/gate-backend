from flask import Flask, request, jsonify
import database  # Importing the database functions from database.py
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "your_secret_key"  # Change this to a strong secret
jwt = JWTManager(app)
CORS(app)

# Hardcoded credentials for demo
valid_users = {
    "guard1": {"password": "guard123", "role": "guard"},
    "admin1": {"password": "admin123", "role": "admin"},
}

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    if username not in valid_users:
        return jsonify({"error": "Invalid username"}), 400

    user = valid_users[username]
    if user["password"] == password:
        access_token = create_access_token(identity={"username": username, "role": user["role"]})
        return jsonify({"access_token": access_token, "role": user["role"]}), 200
    else:
        return jsonify({"error": "Invalid credentials"}), 400
    
@app.route('/protected-route', methods=['GET'])
@jwt_required()
def protected_route():
    current_user = get_jwt_identity()
    return jsonify({"message": "Welcome!", "user": current_user}), 200
    

@app.route('/last_entries', methods=['GET'])
def get_last_entries():
    contact_no = request.args.get('contact_no')
    if not contact_no:
        return jsonify({"error": "Please provide a contact_no"}), 400
    
    try:
        entries = database.fetch_last_five_entries(contact_no)  # New function in database.py
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/add_entry', methods=['POST'])
def add_entry():
    data = request.json
    print  (data)
    # Required fields
    # required_fields = ["name", "contact_no", "destination", "reason", "vehicle_type", "remarks"]
    
    # # Check for missing fields
    # missing_fields = [field for field in required_fields if field not in data]
    # if missing_fields:
    #     return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

    # Optional fields (only included if present)
    if 'vehicle_no' not in data:
        data['vehicle_no'] = None  # Make vehicle_no optional
    if 'vehicle_type' not in data:
        data['vehicle_type'] = None  # Make vehicle_type optional

    # Create the gate entry in the database
    try:
        entry_id = database.create_gate_entry(data)
        return jsonify({"message": "Entry added successfully", "entry_id": entry_id}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/mark_exit', methods=['POST'])
def mark_exit():
    data = request.json
    out_time = data['out_time']
    # Check which parameter is provided to mark the exit
    if 'entry_id' in data:
        success = database.mark_exit_by_id(data['entry_id'], out_time)
    elif 'vehicle_no' in data:
        success = database.mark_exit_by_vehicle(data['vehicle_no'], out_time)
    elif 'contact_no' in data:
        success = database.mark_exit_by_contact(data['contact_no'], out_time)
    else:
        return jsonify({"error": "Provide entry_id, vehicle_no, or contact_no to mark exit"}), 400

    # Return success or failure message
    if success:
        return jsonify({"message": "Exit marked successfully"}), 200
    else:
        return jsonify({"error": "No matching entry found or exit already marked"}), 404

@app.route('/all_entries', methods=['GET'])
def get_all_entries():
    try:
        entries = database.fetch_all_entries()  # Fetch all entries from the database
        return jsonify(entries), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/entries_with_blank_out_time', methods=['GET'])
def entries_with_blank_out_time():
    entries = database.fetch_entries_with_blank_out_time()  # Fetch entries with blank out_time
    if entries:
        return jsonify(entries), 200
    else:
        return jsonify({"message": "No entries with blank out_time found"}), 404

# @app.route('/get_visitor_name', methods=['GET'])
# def get_visitor_name():
#     contact_no = request.args.get('contact_no')
#     if not contact_no:
#         return jsonify({"error": "Please provide a contact_no"}), 400
    
#     # Fetch the visitor's name based on mobile number
#     name = database.get_visitor_name_by_mobile(contact_no)
#     if name:
#         return jsonify({"name": name}), 200
#     else:
#         return jsonify({"error": "Visitor not found"}), 404

@app.route('/get_visitor_details', methods=['GET'])
def get_visitor_details():
    contact_no = request.args.get('contact_no')
    if not contact_no:
        return jsonify({"error": "Please provide a contact_no"}), 400

    # Fetch the visitor's details (name, last vehicle number, and vehicle type)
    visitor_details = database.get_visitor_details_by_mobile(contact_no)
    if visitor_details:
        return jsonify(visitor_details), 200
    else:
        return jsonify({"error": "Visitor not found"}), 404

    
# @app.route('/search_entries', methods=['GET'])
# def search_entries():
#     search_type = request.args.get('search_type')
#     query = request.args.get('query')

#     # Validate parameters
#     if not search_type or not query:
#         return jsonify({"error": "Please provide both search_type and query"}), 400
    
#     try:
#         # Perform the search and retrieve matching entries
#         results = database.search_entries(search_type, query)
#         return jsonify(results), 200
#     except ValueError as e:
#         return jsonify({"error": str(e)}), 400
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500
    

@app.route('/search_entries', methods=['GET'])
def search_visitor_endpoint():
    search_type = request.args.get('search_type')
    query = request.args.get('query')
    print(search_type, query)
    if not search_type or not query:
        return jsonify({"error": "Both 'field' and 'value' are required parameters."}), 400

    # Select the appropriate function based on the field
    if search_type == 'Contact':
        results = database.search_visitor_by_contact(query)
    elif search_type == 'ID':
        results = database.search_visitor_by_id(query)
    elif search_type == 'Name':
        results = database.search_visitor_by_name(query)
    else:
        return jsonify({"error": "Invalid search field provided."}), 400

    return jsonify(results)

@app.route('/search_inside_entries', methods=['GET'])
def search_inside_visitor_endpoint():
    search_type = request.args.get('search_type')
    query = request.args.get('query')
    print(search_type, query)
    if not search_type or not query:
        return jsonify({"error": "Both 'field' and 'value' are required parameters."}), 400

    # Select the appropriate function based on the field
    if search_type == 'Contact':
        results = database.search_inside_visitor_by_contact(query)
    elif search_type == 'ID':
        results = database.search_inside_visitor_by_id(query)
    elif search_type == 'Name':
        results = database.search_inside_visitor_by_name(query)
    else:
        return jsonify({"error": "Invalid search field provided."}), 400

    return jsonify(results)


if __name__ == "__main__":
    app.run(debug=True)
