from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium import webdriver
import sqlite3
from pytz import timezone 
from datetime import datetime
import requests
import time


def send_telegram_message(newly_posted_internships: list[dict]) -> None:
    """
    Sends a message to a Telegram chat with details of newly posted internships.

    Args:
        newly_posted_internships: A list of dictionaries containing details of newly posted internships.
    """
    if len(newly_posted_internships)>0:
        print('Sending Telegram message...')
    bot_token = '5986205629:AAHQGRcXH6xcYEdYD2hyH0RCLlPPu6Sen88'
    chat_id = '919334359'
    for internship_details in newly_posted_internships:
        message = '\n'.join(f"{k.upper()}: {v}" for k, v in internship_details.items())

        url = f'https://api.telegram.org/bot{bot_token}/sendMessage'
        params = {'chat_id': chat_id, 'text': message}

        response = requests.post(url, params=params)

        if response.status_code == 200:
            print('Message sent successfully!')
        else:
            print(f'Something went wrong: {response.text}')
        time.sleep(5)
    
    
def create_db() -> None:
    """
    Creates a SQLite database for storing internship details.
    """
    print('Creating database...')
    conn = sqlite3.connect('internships.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS internships
                    (company_name TEXT, intern_role TEXT, stipend TEXT,
                    duration TEXT, start_date TEXT, dt_posted TEXT,
                    intern_type TEXT, utc TIMESTAMP, PRIMARY KEY (company_name, intern_role, stipend, duration, start_date, intern_type))''')
    print('Database created!')
        
def insert_into_db(new_internships: list[dict]) -> list[dict]:
    """
    Inserts new internships into the database and returns a list of the newly added internships.

    Args:
        new_internships: A list of dictionaries containing details of new internships.

    Returns:
        A list of dictionaries containing details of the newly added internships.
    """
    print('Inserting into database...')
    conn = sqlite3.connect('internships.db')
    cursor = conn.cursor()
    latest_internships= []
    for internship in new_internships:
        cursor.execute(f"SELECT * FROM internships WHERE company_name=? AND intern_role=? AND stipend=? AND duration=? AND start_date=? AND intern_type=?", 
                    (internship['company_name'], internship['intern_role'], internship['stipend'], 
                        internship['duration'], internship['start_date'], internship['intern_type']))
        result = cursor.fetchone()
        
        # if the internship doesn't already exist, insert it into the database
        if not result:
            latest_internships.append(internship)
            cursor.execute("INSERT INTO internships VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
                        (internship['company_name'], internship['intern_role'], internship['stipend'], 
                            internship['duration'], internship['start_date'], internship['dt_posted'], 
                            internship['intern_type'], internship['UTC']))
    conn.commit()
    conn.close()
    print('Database updated!')
    return latest_internships

def initialize_driver() -> webdriver.Chrome:
    """
    Initializes a Firefox webdriver with the given options and returns it.

    Args:
        options: An instance of FirefoxOptions with the desired options set.

    Returns:
        An instance of Firefox webdriver.
    """
    print('Initializing driver...')
    options = Options()
    options.add_argument("--private-window")
    options.add_argument("--disable-web-security")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins-discovery")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-setuid-sandbox")
    options.add_argument("--disable-logging")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36")

    options.add_argument("--headless")

    driver = webdriver.Chrome(options=options,service=Service("/usr/bin/chromedriver"))
    #driver = webdriver.Chrome(options=options)
    print('Driver initialized!')
    return driver

def get_internships(driver: webdriver.Chrome) -> list[dict]:
    """
    Scrapes the internships from the given URL and returns a list of dictionaries containing details of the internships.
    
    Args:
        driver: An instance of Firefox webdriver.
    
    Returns:
        A list of dictionaries containing details of the internships.
    """
    print('Getting internships...')
    url = "https://internshala.com/internships/work-from-home-python-django-internships/"
    driver.get(url)
    try:
        no_thanks_link = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.ID, "no_thanks"))
        )
        no_thanks_link.click()
    except:
        pass
    
    WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.ID, 'internship_list_container_1')))
    
    internship_list_container = driver.find_element(By.ID, 'internship_list_container_1')
    internship_meta_divs = internship_list_container.find_elements(By.CLASS_NAME, 'internship_meta')
    internship_link_divs = internship_list_container.find_elements(By.CLASS_NAME, 'individual_internship')

    new_internships = []
    print(f"Found {len(internship_meta_divs)} internships")
    for internship_meta,internship_link_div in zip(internship_meta_divs,internship_link_divs):
        try:

            # GETTING COMPANY NAME AND ROLE
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'individual_internship_header')))
            company_div = internship_meta.find_element(By.CLASS_NAME, 'individual_internship_header').find_element(By.CLASS_NAME, 'company')
        
            intern_role = company_div.find_element(By.TAG_NAME, 'h3').text
            company_name = company_div.find_element(By.TAG_NAME, 'p').text
            apply_link = internship_link_div.find_element(By.CLASS_NAME, 'btn.btn-secondary.view_detail_button_outline').get_attribute('href')
            print(f"Found {company_name} - {intern_role} - {apply_link}")

            # GETTING START DATE, DURATION AND STIPEND
            WebDriverWait(driver, 60).until(EC.presence_of_element_located((By.CLASS_NAME, 'internship_other_details_container')))
            intern_details_div = internship_meta.find_element(By.CLASS_NAME, 'internship_other_details_container').text
            intern_details = intern_details_div.split(' \n')[0].split('\n')
            print(intern_details)

            start_date = intern_details[1]
            duration = intern_details[3]
            stipend = intern_details[5]
            dt_posted = internship_meta.find_element(By.CLASS_NAME, "posted_by_container").text
            intern_type =internship_meta.find_element(By.CLASS_NAME, "other_label_container").text

            new_internships.append({

                "company_name":company_name,
                "intern_role":intern_role,
                "stipend":stipend,
                'apply_link':apply_link,
                "duration":duration,
                "start_date":start_date,
                "dt_posted":dt_posted,
                'intern_type':intern_type,
                "UTC":str(datetime.now(timezone("Asia/Kolkata")).strftime('%Y-%m-%d %H:%M:%S'))
            })
        except Exception as e:
            print(e)
    print('Internships scraped!')
    return new_internships


if __name__=="__main__":
    print('Starting script...')
    driver = initialize_driver()
    create_db()
    while True:
        python_internships = get_internships(driver)
        newly_posted_internships = insert_into_db(python_internships)
        send_telegram_message(newly_posted_internships)
        print('Sleeping for 30 minutes...')
        time.sleep(60*30)
        

