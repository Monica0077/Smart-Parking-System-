from flask import Flask, render_template, request, redirect, url_for, jsonify
import time
import re
from datetime import datetime
import pytz


app = Flask(__name__)
app.secret_key = "secret_key"  # Needed for session and flashing messages

# Parking system data
parking_slots = {1: None, 2: None, 3: None, 4: None, 5: None, 6: None, 7: None, 8: None, 9: None, 10: None}
fee_per_hour = 50  
entry_times = {}  # To store entry time for each vehicle


IST = pytz.timezone('Asia/Kolkata')

@app.route("/")
def home():
    message = request.args.get("message", "")
    fee_info = f"Parking fee: ₹{fee_per_hour} per hour."
    return render_template("index.html", slots=parking_slots, message=message, fee_info=fee_info)

@app.route("/search_slot", methods=["GET"])
def search_slot():
    vehicle_number = request.args.get("vehicle_number")
    # Search for the vehicle and find the slot number
    slot_number = next((slot for slot, vehicle in parking_slots.items() if vehicle == vehicle_number), None)
    
    if slot_number is not None:
        # Return a JSON response with the slot number
        return jsonify({"found": True, "slot": slot_number})
    else:
        # Return a JSON response indicating vehicle not found
        return jsonify({"found": False, "slot": None})



@app.route("/park", methods=["POST"])
def park_vehicle():
    vehicle_number = request.form.get("vehicle_number")
    available_slot = next((slot for slot, vehicle in parking_slots.items() if vehicle is None), None)

    if available_slot:
        parking_slots[available_slot] = vehicle_number
        entry_times[vehicle_number] = time.time()  # Record the current time
        message = f"Vehicle {vehicle_number} parked in slot {available_slot}."
    else:
        message = "No parking slots available. Please wait for a slot to be freed."
    return redirect(url_for("home", message=message))

@app.route("/release", methods=["POST"])
def release_vehicle():
    slot_number = int(request.form.get("slot_number"))
    if slot_number in parking_slots and parking_slots[slot_number]:
        vehicle_number = parking_slots[slot_number]
        parked_duration = (time.time() - entry_times[vehicle_number]) / 3600  # Convert seconds to hours
        fee = round(parked_duration * fee_per_hour, 2)

        # Get the Indian Standard Time for entry
        entry_time = datetime.fromtimestamp(entry_times[vehicle_number], IST).strftime('%Y-%m-%d %H:%M:%S')
        
        return render_template("payment.html", vehicle_number=vehicle_number, fee=fee, slot_number=slot_number, 
                               entry_time=entry_time, parked_duration=round(parked_duration, 2), 
                               payment_status="paid", error_message=None)
    else:
        message = "Invalid slot number or the slot is already empty."
        return redirect(url_for("home", message=message))

@app.route("/confirm_payment", methods=["POST"])
def confirm_payment():
    vehicle_number = request.form.get("vehicle_number")
    slot_number = int(request.form.get("slot_number"))
    payment_status = request.form.get("payment_status")
    card_number = request.form.get("card_number")
    expiry_date = request.form.get("expiry_date")
    cvv = request.form.get("cvv")

    # Validate card details
    error_message = None
    if not validate_card(card_number, expiry_date, cvv):
        error_message = "Invalid card details. Please check the card number, expiry date, and CVV."

    if error_message:
        # Re-render the payment form with error message
        return render_template("payment.html", vehicle_number=vehicle_number, fee=request.form.get("fee"),
                               slot_number=slot_number, entry_time=request.form.get("entry_time"),
                               parked_duration=request.form.get("parked_duration"), payment_status="not_paid", 
                               error_message=error_message)
    
    # If valid, proceed with releasing vehicle and payment
    if payment_status == "paid":
        # Release the vehicle from the parking slot
        parking_slots[slot_number] = None
        entry_times.pop(vehicle_number, None)  # Remove vehicle entry time
        
        # Get exit time in IST
        exit_time = datetime.now(IST).strftime('%Y-%m-%d %H:%M:%S')

        # Generate receipt
        message = f"Vehicle {vehicle_number} has been released from slot {slot_number}. Thank you for your payment!"
        
        return render_template("receipt.html", vehicle_number=vehicle_number, fee=request.form.get("fee"), 
                               entry_time=request.form.get("entry_time"), exit_time=exit_time, 
                               parked_duration=request.form.get("parked_duration"))
    else:
        message = "Payment failed. Please try again."
        return redirect(url_for("home", message=message))


def validate_card(card_number, expiry_date, cvv):
    # Check if the card number is exactly 16 digits
    if not re.match(r'^\d{16}$', card_number):
        return False
    
    # Validate expiry date (MM/YY format) and check if the expiry date is in the future
    try:
        expiry_month, expiry_year = map(int, expiry_date.split('/'))
        expiry_date = datetime(year=2000 + expiry_year, month=expiry_month, day=1)
        if expiry_date < datetime.now():
            return False  # Expiry date is in the past
    except ValueError:
        return False  # Invalid expiry date format
    
    # Validate CVV (must be exactly 3 digits)
    if not re.match(r'^\d{3}$', cvv):
        return False
    
    return True


if __name__ == "__main__":
    app.run(debug=True)
