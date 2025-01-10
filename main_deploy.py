from flask import Flask, request, jsonify
import database  # Importing the database functions from database.py
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, get_jwt
from flask_ngrok import run_with_ngrok  # Import ngrok # deploy
from pyngrok import ngrok # deploy

app = Flask(__name__)
app.config["JWT_SECRET_KEY"] = "your_secret_key"  # Change this to a strong secret
jwt = JWTManager(app)
CORS(app)

# deploy
# Expose the Flask app to the internet via ngrok
port = 5000
public_url = ngrok.connect(port)
print(f"Ngrok Tunnel URL: {public_url}")

# @app.route('/login', methods=['POST'])
# def login():
#     data = request.json
#     if not data:
#         return jsonify({"error": "Invalid data"}), 400

#     username = data.get("username")
#     password = data.get("password")
#     ip_address = data.get("ip_address")

#     if not username or not password:
#         return jsonify({"error": "Missing required fields"}), 400

#     # Authenticate user using the database
#     authenticated_user = database.authenticate_user(username, password)
#     if not authenticated_user:
#         return jsonify({"error": "Invalid username or password"}), 401

#     # Start session
#     if not database.start_session(username, ip_address):
#         return jsonify({"error": "Failed to create session"}), 500
    
#     # Generate JWT token
#     access_token = create_access_token(identity=authenticated_user)
#     return jsonify({"access_token": access_token, "role": authenticated_user["role"]}), 200
    
# @app.route('/logout', methods=['POST'])
# @jwt_required()
# def logout():
#     current_user = get_jwt_identity()
#     print(current_user)
#     if not current_user:
#         return jsonify({"error": "Invalid or missing token"}), 422
    
#     username = current_user.get("username")

#     # End session
#     if not database.end_session(username):
#         return jsonify({"error": "Failed to end session"}), 500

#     return jsonify({"message": f"User '{username}' has logged out successfully."}), 200
    

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({"error": "Invalid data"}), 400

    username = data.get("username")
    password = data.get("password")
    ip_address = data.get("ip_address")

    if not username or not password:
        return jsonify({"error": "Missing required fields"}), 400

    # Authenticate user using the database
    authenticated_user = database.authenticate_user(username, password)
    if not authenticated_user:
        return jsonify({"error": "Invalid username or password"}), 401

    # Start session
    if not database.start_session(username, ip_address):
        return jsonify({"error": "Failed to create session"}), 500
    
    # Generate JWT token with a string identity (username) and additional claims
    access_token = create_access_token(
        identity=username,  # Use a string for the identity
        additional_claims={"role": authenticated_user["role"]}
    )
    return jsonify({"access_token": access_token, "role": authenticated_user["role"]}), 200


@app.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    # Get the username from the token's identity
    username = get_jwt_identity()
    print("Logging out user:", username)

    # Get additional claims if needed (e.g., role)
    claims = get_jwt()
    role = claims.get("role", "unknown")
    print("Role:", role)

    if not username:
        return jsonify({"error": "Invalid or missing token"}), 422

    # End session
    if not database.end_session(username):
        return jsonify({"error": "Failed to end session"}), 500

    return jsonify({"message": f"User '{username}' has logged out successfully."}), 200


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


# @app.route('/add_entry', methods=['POST'])
# def add_entry():
#     data = request.json
#     print  (data)
#     # Required fields
#     # required_fields = ["name", "contact_no", "destination", "reason", "vehicle_type", "remarks"]
    
#     # # Check for missing fields
#     # missing_fields = [field for field in required_fields if field not in data]
#     # if missing_fields:
#     #     return jsonify({"error": f"Missing fields: {', '.join(missing_fields)}"}), 400

#     # Optional fields (only included if present)
#     if 'vehicle_no' not in data:
#         data['vehicle_no'] = None  # Make vehicle_no optional
#     if 'vehicle_type' not in data:
#         data['vehicle_type'] = None  # Make vehicle_type optional

#     # Create the gate entry in the database
#     try:
#         entry_id = database.create_gate_entry(data)
#         return jsonify({"message": "Entry added successfully", "entry_id": entry_id}), 201
#     except Exception as e:
#         return jsonify({"error": str(e)}), 500

@app.route('/add_entry', methods=['POST'])
def add_entry():
    data = request.json
    print(data)

    # Optional fields (only included if present)
    if 'vehicle_no' not in data:
        data['vehicle_no'] = None  # Make vehicle_no optional
    if 'vehicle_type' not in data:
        data['vehicle_type'] = None  # Make vehicle_type optional

    # Handle the custom destination
    destination = data.get("destination")
    if destination == "Other" and "custom_destination" in data:
        data["destination"] = f"Other - {data['custom_destination']}"  # Prefix custom destination with "Other - "
        del data["custom_destination"]  # Remove custom_destination field after updating the destination

    # Validate the destination field
    if not data.get("destination"):
        return jsonify({"error": "Destination is required"}), 400

    # Create the gate entry in the database
    try:
        entry_id = database.create_gate_entry(data)  # Assuming create_gate_entry handles saving to the DB
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

@app.route('/handle_cancel', methods=['POST'])
def handle_cancel():
    data = request.json
    entry_id = data.get("entry_id")

    if not entry_id:
        return jsonify({"error": "Entry ID is required"}), 400

    try:
        # Call the database function to update the remarks
        success = database.add_remark_wrong_entry(entry_id)
        if success:
            return jsonify({"message": "Remarks updated successfully"}), 200
        else:
            return jsonify({"error": "No matching entry found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

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

@app.route('/guards', methods=['GET'])
def fetch_guards_by_shift():
    shift = request.args.get('shift')
    print(shift)
    if not shift:
        return jsonify({"error": "Shift parameter is required"}), 400

    if shift not in ['morning', 'evening', 'night']:
        return jsonify({"error": "Invalid shift value. Must be 'morning', 'evening', or 'night'"}), 400

    guards = database.get_guards_by_shift(shift)
    if not guards:
        return jsonify({"error": "No guards found for the specified shift"}), 404

    return jsonify({"guards": guards}), 200

@app.route('/all_sessions', methods=['GET'])
@jwt_required()
def all_sessions():
    try:
        from database import get_all_sessions
        sessions = get_all_sessions()
        return jsonify(sessions or []), 200  # Always return an array
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/reset-password', methods=['POST'])
def handle_reset_password():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    username = data.get("username")
    new_password = data.get("newPassword")
    user_type = data.get("userType")  # Optional: Use if roles need extra handling

    if not username or not new_password:
        return jsonify({"error": "Username and new password are required"}), 400

    # Call the database function to reset the password
    success = database.reset_password(username, new_password)

    if success:
        return jsonify({"message": f"Password for user '{username}' has been reset successfully."}), 200
    else:
        return jsonify({"error": f"Failed to reset password for user '{username}'"}), 404

@app.route('/get-password', methods=['GET'])
def get_password():
    username = request.args.get("username")
    if not username:
        return jsonify({"error": "Username is required"}), 400

    # Call the database function to get the old password
    password = database.get_old_password(username)

    if password is None:
        return jsonify({"error": f"User '{username}' not found"}), 404

    return jsonify({"password": password}), 200

@app.route('/admins', methods=['GET'])
def fetch_admins():
    try:
        # Call the database function to fetch admins
        admins = database.get_admins()
        if not admins:
            return jsonify({"error": "No admins found"}), 404
        return jsonify({"admins": admins}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch admins: {e}"}), 500

# if __name__ == "__main__":
#     app.run(debug=True)

# deploy
if __name__ == "__main__":
    app.run(port=port)