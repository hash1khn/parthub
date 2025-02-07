from flask import Flask, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
#from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pandas as pd
from PNP import scrape_pnp
from OGPAP import scrape_ogpap
from TAP import scrape_tap

# Initialize Flask app
app = Flask(__name__)
app.secret_key = '1234456789'

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp.your-email-provider.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your-email@example.com'
app.config['MAIL_PASSWORD'] = 'your-email-password'
app.config['MAIL_DEFAULT_SENDER'] = 'your-email@example.com'

mail = Mail(app)

# Define Car Model (Scraped Data)
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(4), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    row = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    yard = db.Column(db.String(50), nullable=False)
    completed = db.Column(db.Boolean, default=False)  # New field


# Define SavedVehicle Model (User-saved cars)
class SavedVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    min_year = db.Column(db.String(4))
    max_year = db.Column(db.String(4))
    part = db.Column(db.String(100))

# **Updated Function: Scrape and Update Database**
def update_database():
    """Fetches new data from scraping sources and updates the database."""
    try:
        print("Running manual database update...")

        # Scrape data from all sources
        pnp_data = scrape_pnp()
        ogpap_data = scrape_ogpap()
        tap_data = scrape_tap()

        # Combine data into a DataFrame
        columns = ["Year", "Make", "Model", "Row", "Date", "Yard"]
        pnp_df = pd.DataFrame(pnp_data, columns=columns)
        ogpap_df = pd.DataFrame(ogpap_data, columns=columns)
        tap_df = pd.DataFrame(tap_data, columns=columns)
        combined_df = pd.concat([pnp_df, ogpap_df, tap_df], ignore_index=True)

        # Convert 'Date' column to datetime format
        combined_df['Date'] = pd.to_datetime(combined_df['Date'], format='%m/%d/%y', errors='coerce')

        # Remove old cars (older than 15 days)
        fifteen_days_ago = datetime.today().date() - timedelta(days=15)
        
        with app.app_context():
            Car.query.filter(Car.date < fifteen_days_ago).delete()

            # Insert new scraped data
            for _, row in combined_df.iterrows():
                car = Car(
                    year=row['Year'],
                    make=row['Make'],
                    model=row['Model'],
                    row=row['Row'],
                    date=row['Date'].date(),
                    yard=row['Yard']
                )
                db.session.add(car)

            db.session.commit()

        print(f"✅ Database updated successfully at {datetime.now()}")
        return {"success": True, "message": "Database refreshed successfully!"}

    except Exception as e:
        print(f"❌ Error updating database: {str(e)}")
        return {"success": False, "message": f"Error updating database: {str(e)}"}

# Route: Home Page (Car Listings)
@app.route('/')
def index():
    fifteen_days_ago = datetime.today().date() - timedelta(days=15)
    
    # Fetch recent cars, sorted by date (newest first)
    recent_cars = Car.query.filter(Car.date >= fifteen_days_ago).order_by(Car.date.desc()).all()

    # Convert to list for display
    data = [
        {'Year': car.year, 'Make': car.make, 'Model': car.model, 'Row': car.row, 
         'Date': car.date.strftime('%Y-%m-%d'), 'Yard': car.yard}
        for car in recent_cars
    ]

    # Convert to DataFrame for HTML table rendering
    df = pd.DataFrame(data)
    table_html = df.to_html(classes="table table-striped") if not df.empty else "<p>No data available</p>"
    
    return render_template("index.html", table_html=table_html)


# **NEW API: Manual Database Refresh**
@app.route('/api/refresh_database', methods=['POST'])
def refresh_database():
    """Manually refresh the database by scraping new data."""
    result = update_database()
    return jsonify(result), 200 if result["success"] else 500

# Route: Hot Wheels Page (User-saved cars)
@app.route('/hot_wheels')
def hot_wheels():
    return render_template("hot_wheels.html")

# Flask route for the scavenger page
@app.route('/scavenger')
def scavenger():
    return render_template('scavenger.html')

# API: Fetch Scavenger Yards
# API: Fetch filtered Hot Wheels for Scavenger Page
@app.route('/api/scavenger_filtered', methods=['GET'])
def get_scavenger_filtered():
    """Filter Part Hub database cars using the Hot Wheels list and group them by row, including min/max year."""
    days_filter = request.args.get('days', 'all')  
    today = datetime.today().date()

    # Date filtering
    filter_date = None
    if days_filter == "2":
        filter_date = today - timedelta(days=2)
    elif days_filter == "7":
        filter_date = today - timedelta(days=7)

    # Fetch Hot Wheels list with min/max year
    hot_wheels = SavedVehicle.query.all()
    
    # Convert list to dictionary for easy lookup
    hot_wheels_dict = {
        (v.make.lower(), v.model.lower()): (v.min_year, v.max_year) for v in hot_wheels
    }

    # Fetch cars and filter by Hot Wheels list and year range
    query = Car.query
    if filter_date:
        query = query.filter(Car.date >= filter_date)

    filtered_cars = query.all()

    # Group by Yard & Row
    yard_data = {}
    for car in filtered_cars:
        car_key = (car.make.lower(), car.model.lower())

        # Check if the car is in the Hot Wheels list
        if car_key in hot_wheels_dict:
            min_year, max_year = hot_wheels_dict[car_key]

            # Convert min/max year to int if not None
            min_year = int(min_year) if min_year and min_year.isdigit() else None
            max_year = int(max_year) if max_year and max_year.isdigit() else None
            car_year = int(car.year)

            # Ensure the car year falls within the range
            if (min_year is None or car_year >= min_year) and (max_year is None or car_year <= max_year):

                if car.yard not in yard_data:
                    yard_data[car.yard] = {"hotWheelsCount": 0, "vehicles": {}}

                if car.row not in yard_data[car.yard]["vehicles"]:
                    yard_data[car.yard]["vehicles"][car.row] = {
                        "row": car.row,
                        "models": f"{car.make} {car.model}",
                        "completed": False,
                        "years": []
                    }

                # Add car's year if it matches the filter
                yard_data[car.yard]["vehicles"][car.row]["years"].append(car.year)
                yard_data[car.yard]["hotWheelsCount"] += 1

    # Convert row data to list and sort by row number
    for yard in yard_data:
        yard_data[yard]["vehicles"] = sorted(yard_data[yard]["vehicles"].values(), key=lambda x: int(x["row"]))

    return jsonify(yard_data)


@app.route('/api/scavenger_yards/<yard>/rows/<row>', methods=['PUT'])
def update_row_completion(yard, row):
    """Marks a row in a specific yard as completed."""
    data = request.get_json()
    completed_status = data.get('completed', False)

    # Convert row to integer if necessary (in case database stores row as int)
    try:
        row = int(row)
    except ValueError:
        return jsonify({"error": "Invalid row number"}), 400  # Return error if row is not a valid integer

    # Fetch the car that matches the given yard and row
    car = Car.query.filter_by(yard=yard, row=row).first()
    if not car:
        return jsonify({"error": f"Row {row} not found in yard {yard}"}), 404

    # Update the completion status
    car.completed = completed_status
    db.session.commit()

    # Return the updated row so the frontend stays in sync
    return jsonify({
        "message": f"Row {row} in {yard} updated.",
        "yard": yard,
        "row": row,
        "completed": car.completed  # Return updated completed status
    })

# API: Fetch saved vehicles
@app.route('/api/saved_vehicles', methods=['GET'])
def get_saved_vehicles():
    vehicles = SavedVehicle.query.all()
    return jsonify([{
        'id': v.id, 'make': v.make, 'model': v.model,
        'minYear': v.min_year, 'maxYear': v.max_year, 'part': v.part
    } for v in vehicles])

# API: Add a new saved vehicle
@app.route('/api/saved_vehicles', methods=['POST'])
def add_saved_vehicle():
    data = request.json
    new_vehicle = SavedVehicle(
        make=data['make'],
        model=data['model'],
        min_year=data['minYear'],
        max_year=data['maxYear'],
        part=data['part']
    )
    db.session.add(new_vehicle)
    db.session.commit()
    return jsonify({"message": "Vehicle saved!", "id": new_vehicle.id})

# API: Update a saved vehicle
@app.route('/api/saved_vehicles/<int:vehicle_id>', methods=['PUT'])
def update_saved_vehicle(vehicle_id):
    vehicle = SavedVehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404

    data = request.json
    vehicle.make = data['make']
    vehicle.model = data['model']
    vehicle.min_year = data['minYear']
    vehicle.max_year = data['maxYear']
    vehicle.part = data['part']

    db.session.commit()
    return jsonify({"message": "Vehicle updated!"})

# API: Delete a saved vehicle
@app.route('/api/saved_vehicles/<int:vehicle_id>', methods=['DELETE'])
def delete_saved_vehicle(vehicle_id):
    vehicle = SavedVehicle.query.get(vehicle_id)
    if not vehicle:
        return jsonify({"error": "Vehicle not found"}), 404

    db.session.delete(vehicle)
    db.session.commit()
    return jsonify({"message": "Vehicle deleted!"})

# API: Search saved vehicles
@app.route('/api/search_vehicles', methods=['GET'])
def search_vehicles():
    # Get the search query from request args
    search_query = request.args.get('query', '').lower()

    # Search in the saved vehicles (make, model, or part)
    vehicles = SavedVehicle.query.filter(
        (SavedVehicle.make.ilike(f'%{search_query}%')) |
        (SavedVehicle.model.ilike(f'%{search_query}%')) |
        (SavedVehicle.part.ilike(f'%{search_query}%'))
    ).all()

    return jsonify([{
        'id': v.id, 'make': v.make, 'model': v.model,
        'minYear': v.min_year, 'maxYear': v.max_year, 'part': v.part
    } for v in vehicles])

# API: Search for cars based on make, model, or year
@app.route('/api/search_cars', methods=['GET'])
def search_cars():
    search_query = request.args.get('query', '').lower()  # Get the search query
    if not search_query:
        return jsonify([])  # If no query is provided, return an empty list

    # Query the Car model based on the search query (case insensitive)
    cars = Car.query.filter(
        (Car.make.ilike(f'%{search_query}%')) |
        (Car.model.ilike(f'%{search_query}%')) |
        (Car.year.ilike(f'%{search_query}%'))
    ).all()

    # Convert the result to a list of dictionaries
    car_list = [
        {
            'year': car.year,
            'make': car.make,
            'model': car.model,
            'row': car.row,
            'date': car.date.strftime('%Y-%m-%d'),
            'yard': car.yard
        }
        for car in cars
    ]

    return jsonify(car_list)

def send_hotwheels_email():
    """Sends a daily email with the Hot Wheels report."""
    with app.app_context():
        response = get_scavenger_filtered()
        yards_data = response.get_json()

        email_body = "Hot Wheels Report for Today:\n\n"
        for yard, details in yards_data.items():
            email_body += f"{yard} ({details['hotWheelsCount']} Hot Wheels):\n"
            for car in details["vehicles"]:
                email_body += f"  - {car['year']} {car['make']} {car['model']} (Row {car['row']})\n"
            email_body += "\n"

        msg = Message("Daily Hot Wheels Report", recipients=["your-email@example.com"])
        msg.body = email_body
        mail.send(msg)
        print("Daily Hot Wheels Email Sent")


# Scheduler setup to update the database every 24 hours
#scheduler = BackgroundScheduler()
#scheduler.add_job(func=update_database, trigger="interval", days=1)
#scheduler.add_job(func=send_hotwheels_email, trigger="cron", hour=8, minute=0)

#scheduler.start()

# Ensure the scheduler stops on app exit
#import atexit
#atexit.register(lambda: scheduler.shutdown())

# Run the application
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if they don't exist
    app.run(debug=True)