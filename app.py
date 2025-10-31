import firebase_admin
import requests
from bs4 import BeautifulSoup
from firebase_admin import credentials, firestore
from flask import Flask, jsonify, request, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

try:
    cred = credentials.Certificate("serviceAccountKey.json")
    firebase_admin.initialize_app(cred) 
    db = firestore.client()
    print("✅ Firebase connection successful.")
except Exception as e:
    print(f"🔥 Firebase connection failed: {e}")
    db = None

# --- HTML Serving Endpoint ---
@app.route('/')
def home():
    return render_template('index.html')

# --- API Endpoints ---
@app.route('/developers', methods=['GET'])
def get_developers():
    """
    Fetches developers from Firestore AND their live portfolio titles from their websites.
    """
    if not db:
        return jsonify({"error": "Firestore is not initialized."}), 500
    try:
        developers_ref = db.collection('developers').stream()
        developers_list = []
        
        # Set headers to mimic a browser visit
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        for dev in developers_ref:
            dev_data = dev.to_dict()
            dev_data['id'] = dev.id
            
            # --- இதுதான் புதிய அம்சம்: Live-ஆக Website-ல் இருந்து Title-ஐ எடுப்பது ---
            portfolio_url = dev_data.get('portfolioURL')
            if portfolio_url:
                try:
                    # Make a request to the developer's website
                    response = requests.get(portfolio_url, headers=headers, timeout=5)
                    response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
                    
                    # Parse the HTML content to find the title
                    soup = BeautifulSoup(response.content, 'html.parser')
                    title = soup.title.string if soup.title else "Portfolio"
                    dev_data['experienceTitle'] = title.strip()
                except requests.exceptions.RequestException as e:
                    # If the website is down or there's an error, set a default title
                    print(f"Could not fetch title for {portfolio_url}: {e}")
                    dev_data['experienceTitle'] = "View Portfolio"
            
            developers_list.append(dev_data)
            
        return jsonify(developers_list), 200
    except Exception as e:
        print(f"An error occurred in /developers endpoint: {e}")
        return jsonify({"error": str(e)}), 500


@app.route('/book', methods=['POST'])
def book_appointment():
    # இந்த பகுதியில் எந்த மாற்றமும் இல்லை. It works as before.
    if not db:
        return jsonify({"error": "Firestore is not initialized."}), 500
    try:
        data = request.json
        dev_id = data['developerId']
        time_slot = data['timeSlot']
        
        appointments_ref = db.collection('appointments')
        query = appointments_ref.where('developerId', '==', dev_id).where('timeSlot', '==', time_slot).limit(1)
        existing_appointments = list(query.stream())

        if len(existing_appointments) > 0:
            return jsonify({"success": False, "message": "Sorry, this time slot is already booked!"}), 409

        db.collection('appointments').add({
            'developerId': dev_id,
            'timeSlot': time_slot,
            'studentName': data['studentName'],
            'studentNumber': data['studentNumber'],
            'timestamp': firestore.SERVER_TIMESTAMP
        })
        return jsonify({"success": True, "message": "Appointment booked successfully!"}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- Run the App ---
if __name__ == '__main__':

    app.run(debug=True, port=5000)

