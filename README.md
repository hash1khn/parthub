## 📦 Part Hub

### 🔍 Overview
**Part Hub** is a web application designed to automate the scraping and management of car parts data from multiple sources. The platform integrates data from sources like PNP, OG PAP, and TAP, providing users with up-to-date information on car parts availability across various yards.

### 🚀 Features
- **Automated Data Scraping:** Collects car part data from multiple sources and updates the database.
- **Scheduled Database Updates:** Automatically refreshes the database daily using PythonAnywhere's task scheduler.
- **Search Functionality:** Quickly search for cars by make, model, or year.
- **Duplicate Removal:** Ensures unique entries by detecting and removing duplicate records.
- **Email Reports:** Sends daily Hot Wheels reports via Brevo SMTP.
- **Scavenger View:** View Hot Wheels data with row-level filtering.
- **Manual Refresh:** Trigger database updates manually with a single click.

### 🛠️ Technologies Used
- **Python / Flask**: Backend web framework
- **SQLite**: Lightweight database
- **SQLAlchemy**: Database ORM
- **Pandas**: Data manipulation and analysis
- **Bootstrap**: Frontend styling
- **JavaScript**: Frontend interactivity
- **Brevo SMTP**: Email service for transactional emails
- **PythonAnywhere**: Cloud hosting and scheduled task management

### 📂 Folder Structure
```
/mysite
|-- app.py                 # Main Flask application
|-- update_db.py           # Script for scheduled database updates
|-- PNP.py                 # Data scraper for PNP
|-- OGPAP.py               # Data scraper for OG PAP
|-- TAP.py                 # Data scraper for TAP
|-- requirements.txt       # Project dependencies
|-- static/
|   |-- css/
|   |   |-- styles.css     # Custom styles
|   |-- js/
|       |-- search.js      # Frontend JavaScript for searching
|-- templates/
|   |-- index.html         # Homepage template
|   |-- hot_wheels.html    # Hot Wheels view template
|   |-- scavenger.html     # Scavenger view template
|-- cars.db                # SQLite database
```

### 📝 How to Use
1. **Clone the Repository:**
   ```bash
   git clone https://github.com/yourusername/parthub.git
   cd parthub
   ```

2. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the Application Locally:**
   ```bash
   python app.py
   ```

4. **Set Up Automatic Updates on PythonAnywhere:**
   - Upload `update_db.py` to PythonAnywhere.
   - Schedule a daily task to run:
     ```bash
     /home/yourusername/.virtualenvs/flaskk/bin/python /home/yourusername/mysite/update_db.py
     ```

5. **Access the Application:**
   - Visit `http://yourdomain.pythonanywhere.com` in your browser.

### 🌐 Deployment
The application is deployed on PythonAnywhere, ensuring continuous operation and automated database updates without relying on your local machine.

### 📧 Contact
For any questions or feedback, please open an issue in the repository or contact me at hashirahmedkhan123@gmail.com
