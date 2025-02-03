from flask import Flask, render_template
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

# Define the Car model
class Car(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    year = db.Column(db.String(4), nullable=False)
    make = db.Column(db.String(50), nullable=False)
    model = db.Column(db.String(50), nullable=False)
    row = db.Column(db.String(50), nullable=False)
    date = db.Column(db.Date, nullable=False)
    yard = db.Column(db.String(50), nullable=False)

# Function to scrape and update the database in the background
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

    # Delete old cars (older than 16 days)
    sixteen_days_ago = datetime.today().date() - timedelta(days=16)
    
    with app.app_context():
        Car.query.filter(Car.date < sixteen_days_ago).delete()

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

# Flask route for the index page
@app.route('/')
def index():
    today = datetime.today().date()
    fifteen_days_ago = today - timedelta(days=15)

    # Fetch recent data directly from the database
    recent_cars = Car.query.filter(Car.date >= fifteen_days_ago).all()
    data = [
        {'Year': car.year, 'Make': car.make, 'Model': car.model, 'Row': car.row, 
         'Date': car.date.strftime('%Y-%m-%d'), 'Yard': car.yard}
        for car in recent_cars
    ]

    df = pd.DataFrame(data)
    table_html = df.to_html(classes="table table-striped") if not df.empty else "<p>No data available</p>"
    
    return render_template("index.html", table_html=table_html)

# Flask route for the hot_wheels page
@app.route('/hot_wheels')
def hot_wheels():
    cars = Car.query.all()
    data = [
        {'Year': car.year, 'Make': car.make, 'Model': car.model, 'Row': car.row, 
         'Date': car.date.strftime('%Y-%m-%d'), 'Yard': car.yard}
        for car in cars
    ]
    df = pd.DataFrame(data)
    table_html = df.to_html(classes="table table-striped") if not df.empty else "<p>No data available</p>"
    return render_template("hot_wheels.html", table_html=table_html)

# Scheduler setup to update the database every 24 hours
scheduler = BackgroundScheduler()
scheduler.add_job(func=update_database, trigger="interval", days=1)
scheduler.start()

# Ensure the scheduler stops on app exit
import atexit
atexit.register(lambda: scheduler.shutdown())

# Main entry point
if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create database tables if they don't exist
        if not Car.query.first():  # Only run scraping if database is empty
            update_database()
    app.run(debug=True)
