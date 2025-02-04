from flask import Flask, render_template, request, jsonify, url_for
from flask_sqlalchemy import SQLAlchemy
from apscheduler.schedulers.background import BackgroundScheduler
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

# Define Car Model (Scraped Data)
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(4), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    row = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    yard = db.Column(db.String(50), nullable=False)

# Define SavedVehicle Model (User-saved cars)
class SavedVehicle(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    min_year = db.Column(db.String(4))
    max_year = db.Column(db.String(4))
    part = db.Column(db.String(100))

# Function to scrape and update the database
def update_database():
    print("Running background database update...")
    
    # Scrape data from all sources
    pnp_data = scrape_pnp()
    ogpap_data = scrape_ogpap()
    tap_data = scrape_tap()

    # Combine data into a single DataFrame
    columns = ["Year", "Make", "Model", "Row", "Date", "Yard"]
    pnp_df = pd.DataFrame(pnp_data, columns=columns)
    ogpap_df = pd.DataFrame(ogpap_data, columns=columns)
    tap_df = pd.DataFrame(tap_data, columns=columns)
    combined_df = pd.concat([pnp_df, ogpap_df, tap_df], ignore_index=True)

    # Convert 'Date' column to datetime
    combined_df['Date'] = pd.to_datetime(combined_df['Date'], format='%m/%d/%y', errors='coerce')

    # Delete old cars (older than 15 days)
    fifteen_days_ago = datetime.today().date() - timedelta(days=15)
    
    with app.app_context():
        Car.query.filter(Car.date < fifteen_days_ago).delete()

        # Add new cars to the database
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
    print(f"Database updated successfully at {datetime.now()}")

# Route: Home Page (Car Listings)
@app.route('/')
def index():
    fifteen_days_ago = datetime.today().date() - timedelta(days=15)
    recent_cars = Car.query.filter(Car.date >= fifteen_days_ago).all()

    data = [
        {'Year': car.year, 'Make': car.make, 'Model': car.model, 'Row': car.row, 
         'Date': car.date.strftime('%Y-%m-%d'), 'Yard': car.yard}
        for car in recent_cars
    ]

    df = pd.DataFrame(data)
    table_html = df.to_html(classes="table table-striped") if not df.empty else "<p>No data available</p>"
    
    return render_template("index.html", table_html=table_html)

# Route: Hot Wheels Page (User-saved cars)
@app.route('/hot_wheels')
def hot_wheels():
    return render_template("hot_wheels.html")

# Flask route for the scavenger page
@app.route('/scavenger')
def scavenger():
    return render_template('scavenger.html')

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


# Scheduler setup to update the database every 24 hours
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_database, trigger="interval", days=1)
scheduler.start()

# Ensure the scheduler stops on app exit
import atexit
atexit.register(lambda: scheduler.shutdown())

# Run the application
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist
        if not Car.query.first():  # Only scrape if the database is empty
            update_database()
    app.run(debug=True)
