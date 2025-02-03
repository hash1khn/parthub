from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
import re
import pandas as pd
from datetime import datetime

# Function to scrape data from PNP (row52.com)
def scrape_pnp():
    url = "https://www.row52.com/Search/?YMMorVin=YMM&Year=&V1=&V2=&V3=&V4=&V5=&V6=&V7=&V8=&V9=&V10=&V11=&V12=&V13=&V14=&V15=&V16=&V17=&ZipCode=84010&Page=1&ModelId=&MakeId=&LocationId=&IsVin=false&Distance=50"
    driver = webdriver.Chrome()
    driver.get(url)

    # Wait for the page to load and fetch items
    wait = WebDriverWait(driver, 10)
    rows = wait.until(lambda d: d.find_elements(By.XPATH, "//div[@class='row']"))

    # Function to convert the date format
    def convert_date(date_string):
        try:
            # Convert from 'xxx xx, xxxx' to 'xx/xx/xx'
            date_obj = datetime.strptime(date_string, "%b %d, %Y")
            return date_obj.strftime("%m/%d/%y")
        except ValueError:
            return None

    # Function to extract year, make, and model from the car name
    def extract_year_make_model(name):
        if name:
            match = re.match(r'(\d{4})\s+([A-Za-z]+)\s+(.*)', name)
            if match:
                year = match.group(1)
                make = match.group(2)
                model = match.group(3)
                return year, make, model
        return None, None, None

    # Extract car names, details, and dates
    car_info = []
    for row in rows:
        name = re.sub(r"\s+", " ", row.find_element(By.XPATH, ".//a[@itemprop='description']/strong").text).strip() \
            if row.find_elements(By.XPATH, ".//a[@itemprop='description']/strong") else None
        row_info = re.sub(r"\s+", " ", row.find_element(By.XPATH, ".//div[@class='list-row-right']/strong").text).strip() \
            if row.find_elements(By.XPATH, ".//div[@class='list-row-right']/strong") else None
        date_info = convert_date(
            re.sub(r"\s+", " ", row.find_elements(By.XPATH, ".//div[@class='list-row-right']/strong")[1].text).strip()
        ) if len(row.find_elements(By.XPATH, ".//div[@class='list-row-right']/strong")) > 1 else None

        year, make, model = extract_year_make_model(name)

        if year and make and model and row_info and date_info:
            car_info.append({
                "Year": year,
                "Make": make,
                "Model": model,
                "Row": row_info,
                "Date": date_info,
                "Yard": "PNP",
            })

    driver.quit()

    return car_info
