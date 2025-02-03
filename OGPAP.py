from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from datetime import datetime
import pandas as pd

# Function to scrape data from OG PAP (utpap.com)
def scrape_ogpap():
    url = "https://utpap.com/ogden-arrivals/"
    driver = webdriver.Chrome()
    driver.get(url)

    # Wait for the page to load and fetch both odd and even rows
    wait = WebDriverWait(driver, 10)
    rows = wait.until(lambda d: d.find_elements(By.XPATH, "//tr[@class='odd' or @class='even']"))

    car_info = []

    # Iterate over the rows and extract car details
    for car in rows:
        year = car.find_element(By.XPATH, "./td[1]").text
        make = car.find_element(By.XPATH, "./td[2]").text
        model = car.find_element(By.XPATH, "./td[3]").text
        row = car.find_element(By.XPATH, "./td[7]").text
        date_str = car.find_element(By.XPATH, "./td[8]").text

        # Convert date string into datetime object (use 2-digit year format)
        try:
            date = datetime.strptime(date_str, '%m/%d/%y')  # Adjusted format for 2-digit year
        except ValueError:
            print(f"Skipping car due to invalid date format: {date_str}")
            continue

        # Store car info with the date as a datetime object
        car_info.append((year, make, model, row, date))

    # Sort the car info list by the date in descending order (newest first)
    car_info.sort(key=lambda x: x[4], reverse=True)  # Sorting by the 5th element (date), newest first

    car_list = []

    # Create dictionary for each car and append to car_list
    for car in car_info:
        car_item = {
            "Year": car[0],
            "Make": car[1],
            "Model": car[2],
            "Row": car[3],
            "Date": car[4].strftime('%m/%d/%y'),  # Format the date for readability
            "Yard": "OG PAP",
        }

        car_list.append(car_item)

    driver.quit()

    return car_list
