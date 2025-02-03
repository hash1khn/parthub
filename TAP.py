from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import pandas as pd
from datetime import datetime, timedelta

# Function to scrape data from TAP (junk-yard.herokuapp.com)
def scrape_tap():
    # Setup the driver
    url = "http://junk-yard.herokuapp.com/"
    driver = webdriver.Chrome()
    driver.get(url)

    # Function to scrape car data from the page
    def scrape_page():
        wait = WebDriverWait(driver, 10)
        rows = wait.until(lambda d: d.find_elements(By.XPATH, "//div[@class='carWrapper']"))

        car_list = []

        for item in rows:
            try:
                year = item.find_element(By.XPATH, ".//p[1]").text
                make = item.find_element(By.XPATH, ".//p[2]").text
                model = item.find_element(By.XPATH, ".//p[3]").text
                row = item.find_element(By.XPATH, ".//p[5]").text
                age = item.find_element(By.XPATH, ".//p[7]").text
                yard = item.find_element(By.XPATH, ".//p[6]").text

                # Convert the "age" into an integer (days at the junkyard)
                age_days = int(age) if age.isdigit() else None

                # Get the current date
                today = datetime.today()

                # If the age is valid (i.e., it's a number of days), calculate the arrival date
                if age_days is not None:
                    # Subtract the number of days the car has been at the junkyard from today
                    arrival_date = today - timedelta(days=age_days)

                    # Format the arrival date as mm/dd/yy
                    arrival_date = arrival_date.strftime('%m/%d/%y')
                else:
                    arrival_date = None

                car_item = {
                    "Year": year,
                    "Make": make,
                    "Model": model,
                    "Row": row,
                    "Date": arrival_date,
                    "Yard": yard,
                }

                # Add the car_item to the list inside the try block
                car_list.append(car_item)
            except Exception as e:
                print(f"Error extracting data for one car: {e}")

        return car_list

    # Scrape the page for all cars
    print("Scraping the page for cars...")
    car_list = scrape_page()

    # Close the driver
    driver.quit()

    # Create the DataFrame from the car_list
    df = pd.DataFrame(car_list)

    # Convert the 'Date' column to datetime format for sorting and filtering
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%y', errors='coerce')

    # Sort the DataFrame by 'Date' in descending order
    df_sorted = df.sort_values(by='Date', ascending=False)

    # Filter to exclude cars older than 30 days
    today = datetime.today()
    fifteen_days_ago = today - timedelta(days=15)

    # Filter out cars older than 30 days
    df_filtered = df_sorted[df_sorted['Date'] >= fifteen_days_ago]

    # Reset the index so it starts from 0
    df_filtered_reset = df_filtered.reset_index(drop=True)

    # Reformat the 'Date' column back to mm/dd/yy format
    df_filtered_reset['Date'] = df_filtered_reset['Date'].dt.strftime('%m/%d/%y')

    return df_filtered_reset
