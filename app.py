from flask import Flask, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
#from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import pandas as pd
from PNP import scrape_pnp
from OGPAP import scrape_ogpap
from TAP import scrape_tap
from sqlalchemy import func
from flask import jsonify
from collections import defaultdict



# Initialize Flask app
app = Flask(__name__)
app.secret_key = '1234456789'

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cars.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Email Configuration
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = '859985001@smtp-brevo.com'
app.config['MAIL_PASSWORD'] = '4Eg6K1w0xfnbdWr7'
app.config['MAIL_DEFAULT_SENDER'] = 'hashirahmedkhan123@gmail.com'

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
    """Fetches new data from scraping sources and updates the database while avoiding duplicates."""
    try:
        print("🔄 Running manual database update...")

        # Scrape data from all sources
        print("🔍 Scraping PNP data...")
        pnp_data = scrape_pnp()
        print("✅ Scraped", len(pnp_data), "cars from PNP.")

        print("🔍 Scraping OG PAP data...")
        ogpap_data = scrape_ogpap()
        print("✅ Scraped", len(ogpap_data), "cars from OG PAP.")

        print("🔍 Scraping TAP data...")
        tap_data = scrape_tap()
        print("✅ Scraped", len(tap_data), "cars from TAP.")

        # Combine data into a DataFrame
        columns = ["Year", "Make", "Model", "Row", "Date", "Yard"]
        combined_df = pd.concat([
            pd.DataFrame(pnp_data, columns=columns),
            pd.DataFrame(ogpap_data, columns=columns),
            pd.DataFrame(tap_data, columns=columns)
        ], ignore_index=True)

        # Convert 'Date' column to datetime format
        combined_df['Date'] = pd.to_datetime(combined_df['Date'], format='%m/%d/%y', errors='coerce')

        # Remove old cars (older than 15 days)
        fifteen_days_ago = datetime.today().date() - timedelta(days=15)

        with app.app_context():
            print("🗑️ Removing cars older than 15 days...")
            db.session.query(Car).filter(Car.date < fifteen_days_ago).delete()

            # Get all existing cars in the database to prevent duplicates
            existing_cars = set(
                (car.year, car.make.lower(), car.model.lower(), car.row, car.yard, car.date)
                for car in Car.query.all()
            )

            new_cars = []
            for _, row in combined_df.iterrows():
                car_tuple = (row['Year'], row['Make'].lower(), row['Model'].lower(), row['Row'], row['Yard'], row['Date'].date())

                if car_tuple not in existing_cars:  # Avoid inserting duplicates
                    new_cars.append(Car(
                        year=row['Year'],
                        make=row['Make'],
                        model=row['Model'],
                        row=row['Row'],
                        date=row['Date'].date(),
                        yard=row['Yard']
                    ))
                    existing_cars.add(car_tuple)  # Add to the set to prevent further duplicates

            if new_cars:
                db.session.bulk_save_objects(new_cars)  # Faster batch insertion
                db.session.commit()
                print(f"✅ {len(new_cars)} new cars added to the database!")
                return {"success": True, "message": f"{len(new_cars)} new cars added"}
            else:
                print("✅ No new cars found. Database is already up to date.")
                return {"success": False, "message": "No new cars available"}

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

@app.route('/api/remove_duplicates', methods=['DELETE'])
def remove_duplicates():
    """Find and remove duplicate car records from the database."""
    print("🔍 Checking for duplicate entries in the database...")

    try:
        # Identify duplicate cars based on (year, make, model, row, yard, date)
        duplicates = db.session.query(
            Car.year, Car.make, Car.model, Car.row, Car.yard, Car.date,
            db.func.count().label("count")
        ).group_by(Car.year, Car.make, Car.model, Car.row, Car.yard, Car.date).having(db.func.count() > 1).all()

        if not duplicates:
            print("✅ No duplicates found in the database.")
            return jsonify({"success": False, "message": "No duplicates found"}), 200

        total_deleted = 0
        for duplicate in duplicates:
            year, make, model, row, yard, date, count = duplicate

            # Get all duplicate records
            duplicate_records = Car.query.filter_by(
                year=year, make=make, model=model, row=row, yard=yard, date=date
            ).all()

            # Keep only one record, delete the rest
            for car in duplicate_records[1:]:  # Skip the first record
                db.session.delete(car)
                total_deleted += 1

        # Commit changes
        db.session.commit()

        print(f"✅ {total_deleted} duplicate records deleted.")
        return jsonify({"success": True, "message": f"{total_deleted} duplicate cars removed"}), 200

    except Exception as e:
        print(f"❌ ERROR removing duplicates: {e}")
        return jsonify({"success": False, "message": "Error removing duplicates"}), 500


# API: Fetch Scavenger Yards
# API: Fetch filtered Hot Wheels for Scavenger Page

@app.route('/api/scavenger_filtered', methods=['GET'])
def get_scavenger_filtered():
    """Filter Part Hub database cars using the Hot Wheels list and group them by row, ensuring no duplicate years."""
    
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
        (v.make.lower(), v.model.lower()): (int(v.min_year) if v.min_year and v.min_year.isdigit() else None,
                                            int(v.max_year) if v.max_year and v.max_year.isdigit() else None)
        for v in hot_wheels
    }

    # Fetch cars and apply date filtering
    query = Car.query
    if filter_date:
        query = query.filter(Car.date >= filter_date)

    filtered_cars = query.all()

    # Group by Yard & Row
    yard_data = defaultdict(lambda: {"hotWheelsCount": 0, "vehicles": defaultdict(list)})

    for car in filtered_cars:
        car_key = (car.make.lower(), car.model.lower())

        # Check if the car is in the Hot Wheels list
        if car_key in hot_wheels_dict:
            min_year, max_year = hot_wheels_dict[car_key]
            car_year = int(car.year)

            # Ensure the car year falls within the valid range
            if (min_year is None or car_year >= min_year) and (max_year is None or car_year <= max_year):

                row = str(car.row)  # Convert row to string to avoid mismatches
                vehicle_key = f"{car.make}-{car.model}-{car.year}"  # Unique key to prevent duplicates

                # Ensure unique entries per row
                if vehicle_key not in {f"{v['make']}-{v['model']}-{v['year']}" for v in yard_data[car.yard]["vehicles"][row]}:
                    yard_data[car.yard]["vehicles"][row].append({
                        "row": row,
                        "make": car.make,
                        "model": car.model,
                        "year": car.year,
                        "completed": car.completed
                    })

                    # **Increment hotWheelsCount only once per unique vehicle**
                    yard_data[car.yard]["hotWheelsCount"] += 1

    # Convert defaultdicts back to normal dicts and sort rows numerically
    final_data = {yard: {"hotWheelsCount": data["hotWheelsCount"], "vehicles": sorted(data["vehicles"].items(), key=lambda x: int(x[0]))} for yard, data in yard_data.items()}

    return jsonify(final_data)






@app.route('/api/completed_status', methods=['GET'])
def get_completed_status():
    completed_count = Car.query.filter_by(completed=True).count()
    incomplete_count = Car.query.filter_by(completed=False).count()

    return jsonify({
        "completed_cars": completed_count,
        "incomplete_cars": incomplete_count
    })

@app.route('/api/scavenger_yards/<yard>/rows/<row>/vehicles/<make>/<model>/<year>', methods=['PUT'])
def update_vehicle_completion(yard, row, make, model, year):
    """Marks a specific vehicle (make, model, and year) in a yard row as completed."""
    data = request.get_json()
    completed_status = data.get('completed', False)

    try:
        row = int(row)
        year = int(year)
    except ValueError:
        return jsonify({"error": "Invalid row or year number"}), 400

    # Decode encoded URL parameters
    yard = yard.replace("%20", " ")  # Handle spaces in yard names
    make = make.replace("%20", " ")
    model = model.replace("%20", " ")

    # Debugging: Print received parameters
    print(f"Updating Vehicle: Yard={yard}, Row={row}, Make={make}, Model={model}, Year={year}, Completed={completed_status}")

    # Fetch the specific car
    car = Car.query.filter(
        Car.yard.ilike(yard),  # Case-insensitive matching
        Car.row == row,
        func.lower(Car.make) == make.lower(),
        func.lower(Car.model) == model.lower(),
        Car.year == year
    ).first()

    if not car:
        return jsonify({"error": f"No matching car found in row {row} of yard {yard}"}), 404

    # Update completion status
    car.completed = completed_status
    db.session.commit()

    return jsonify({
        "message": f"✅ Updated: {year} {make} {model} in row {row} of {yard}",
        "yard": yard,
        "row": row,
        "make": make,
        "model": model,
        "year": year,
        "completed": completed_status
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
@app.route('/send_hotwheels_email', methods=['POST'])
def send_hotwheels_email():
    """Sends a daily email with the Hot Wheels report via Brevo SMTP."""
    try:
        # Fetch the latest Hot Wheels data
        with app.app_context():
            response = get_scavenger_filtered()
            yards_data = response.get_json()  # Convert Response to JSON

        # Generate email content
        email_body = "<h2>Hot Wheels Report for Today</h2><ul>"

        for yard, details in yards_data.items():
            email_body += f"<li><b>{yard} ({details['hotWheelsCount']} Hot Wheels)</b></li><ul>"

            for row_number, vehicles in details["vehicles"]:  # Row-wise grouping
                for car in vehicles:  # Loop through cars in each row
                    email_body += f"<li>{car['year']} {car['make']} {car['model']} (Row {row_number})</li>"

            email_body += "</ul>"

        email_body += "</ul>"

        # Create the email message
        msg = Message(
            subject="Daily Hot Wheels Report",
            recipients=["justbrown5678@gmail.com"],  # Replace with actual recipient
            html=email_body
        )

        # Send email using Flask-Mail
        mail.send(msg)

        return jsonify({"success": True, "message": "Hot Wheels email sent successfully!"}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500



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
    