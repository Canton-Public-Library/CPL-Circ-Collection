from datetime import date, datetime, timedelta
import requests
import json
import csv
import psycopg2
import pandas as pd
import numpy as np
import os
import sys 
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from config import load_config

# This script retrieves previous-day data from the SenSource Vea API, the SierraDNA database, and the MeL table and appends it to a csv file.
# There is an optional manual mode that allows users to enter custom dates. This can be accessed by adding "manual" as a command-line argument.
# The clean_upload_append.bat file runs this script at 12:15 AM every day. 
# To properly run this file, there needs to be a config.ini file in the same directory. 

def create_new_row():
    """Returns a Pandas series to store the data in a single row
    """
    data = pd.Series(index = ['Id', 'Date', 'DoorCount', 'CheckedOut', 'TotalSelfCheck', 'DeskCheckOut', 
                            'Renewed', 'TotalCheckedIn', 'TotalCheckedOutReporting', 'Holds', 'New Patrons', 
                            'New Canton Patrons', 'CurbAppt', 'ILL Lent', 'ILL Borrowed', 'Day of Week', 
                            'Month', 'Year', 'Day', 'Day of Week Index', 'Comments'], 
                            dtype = 'int')
    data = data.replace({np.nan: None}) # Convert all NaN values to None (shows up as blank instead of 'NaN' on CSV files)
    return data


def get_token(login_config):
    """Returns an access token from SenSource.
    login_config is the Vea section from the config file.
    """
    url = login_config['auth_url']
    client_id = login_config['client_id']
    client_secret = login_config['client_secret']
    cred = {
        'grant_type':'client_credentials',
        'client_id':client_id,
        'client_secret':client_secret
    }
    response = requests.post(url, json = cred)
    response.close()
    return response.json()['access_token'] #returns access token VALUE


def filter_vea(data):
    """Filters the data from Vea API. So far only filters for door count, 
    but may be more useful when looking for more data.
    data is a dictionary containing the Vea API data
    Returns: door count int
    """
    doorcount = data['sumins']
    return doorcount


def get_vea(export, date, vea_config):
    """Retrieves data from Vea API
    export is the new row that will be appended to the file.
    date specifies which date to get data from. Default is 'yesterday'.
    vea_config is the Vea section from the config file.
    Returns: dictionary containing results
    """
    url = vea_config['url']
    
    authtoken = get_token(vea_config) #access token value
    header = {
        'Authorization':'Bearer ' + str(authtoken),
        'Content-type':'application/json'
    }
    
    if date == 'yesterday':
        params = {
        'relativeDate':date,
        'dateGroupings':'day',
        'entityType':'sensor',
        'metrics':'ins',
        }
    else:
        date_string = str(date) 
        start = datetime(year=int(date_string[0:4]), 
                        month=int(date_string[4:6]), 
                        day=int(date_string[6:8])) 
        end = start + timedelta(days=1)
        params = {
        'relativeDate':'custom',
        'startDate':start,
        'endDate':end,
        'dateGroupings':'day',
        'entityType':'sensor',
        'metrics':'ins',
        }

    response = requests.get(url, headers = header, params = params)

    if response.status_code == 200:
        print('API retrieval success:', response.status_code)
        raw_data = response.json()['results']
        for item in raw_data:
            if item['name'] == 'Main Entrance': # look for dictionary that contains main entrance ins
                export['DoorCount'] = filter_vea(item) # add sumins to the export row
                break
        print("Successfully retrieved Vea API data")
    else: 
        print('Error:', response.status_code)
    response.close()


def get_sierra(export, mode, sierra_config):
    """Connects to the Sierra database and collects circulation data
    export is the new row that will be appended to the file.
    mode is the date mode to query. Either yesterday or custom date.
    sierra_config is the SierraDNA section from the config file.
    Returns: circulation data as a tuple object.
    """
    conn = psycopg2.connect(
        database = sierra_config['database'],
        host = sierra_config['host'],
        user = sierra_config['user'],
        password = sierra_config['password'],
        port = sierra_config['port']
    )

    if mode == 'yesterday':
        date = "(current_date - interval '1 day')"
    else:
        date = f"'{mode}'" # set date to custom date

    circ = f"""select to_char(max(date(transaction_gmt)),'MM/DD/YYYY') as date,
        count(case when (op_code = 'o') then op_code end) as checkedout,
        count(case when (op_code = 'o' and application_name like '%selfcheck') then op_code end) as totalselfcheck,
        count(case when (op_code = 'o' and application_name = 'sierra') then op_code end) as deskcheckout,
        count(case when (op_code = 'r') then op_code end) as renewed,
        count(case when (op_code = 'i') then op_code end) as totalcheckedin,
        count(case when (op_code = 'o' or op_code ='r') then op_code end) as totalcheckedoutreporting,
        count(case when (op_code like 'n%') then op_code end) as holds
    from sierra_view.circ_trans 
    where date(transaction_gmt) = date({date})::date;"""

    new_patrons = f"""SELECT count(*)
        FROM sierra_view.patron_view
        JOIN sierra_view.record_metadata
        ON sierra_view.patron_view.id = sierra_view.record_metadata.id
        WHERE sierra_view.record_metadata.record_type_code = 'p'
        AND date(creation_date_gmt) = date({date});"""

    new_canton = f"""SELECT count(*)
        FROM sierra_view.patron_view
        JOIN sierra_view.record_metadata
        ON sierra_view.patron_view.id = sierra_view.record_metadata.id
        WHERE sierra_view.record_metadata.record_type_code = 'p'
        AND date(creation_date_gmt) = date({date})
        AND barcode LIKE '25149%';"""

    sql_data = []
    cursor = conn.cursor()
    cursor.execute(circ) # add circ data to list
    sql_data += (cursor.fetchone()) 
    cursor.execute(new_patrons) # add number of new patrons
    sql_data += (cursor.fetchone()) 
    cursor.execute(new_canton) # add number of new patrons from canton
    sql_data += (cursor.fetchone()) 
    conn.close()

    export['Date'] = sql_data[0] # add date to the export row
    export[3:12] = sql_data[1:10] # add rest of sql data to export row
    print("Successfully retrieved SierraDNA data")


def get_mel(export, date, mel_config):
    """Retrieves data on interlibrary loans and borrowing from MeL website
    date- because the site does not 
    support specific dates, "manual" mode on this will not work.
    export is the new row that will be appended to the file.
    date- because the site does not support specific dates, "manual" mode on this will not work.
    mel_config is the MeL section from the config file.
    """ 
    if date != 'yesterday': 
        export['Comments'] = 'manual entry required for ILL lent and ILL borrowed'
        return

    url = mel_config['url'] 
    cpl = mel_config['code'] # get library code

    driver = webdriver.Chrome(service = Service(ChromeDriverManager().install()))
    driver.get(url)

    select_frame = driver.find_element(By.XPATH, '/html[1]/frameset[1]/frameset[2]/frame[2]') # locates frame containing the data table
    driver.switch_to.frame(select_frame) # switches to frame containing the data table

    table = driver.find_element(By.XPATH, r'/html[1]/body[1]/center[2]')
    
    # check if Canton Public Library is in the table. If not, the ILL Lent and Borrowed fields will be left blank.
    if cpl not in table.text: 
        print("Interlibrary data not found.")
        return
        
    # find ILL lent
    index = 3 
    while True:  
        html_row = driver.find_element(By.XPATH, f'//tbody/tr[{index}]/td[1]')
        if cpl in html_row.text:  # looks for the row number of zv052
            break
        index += 1 
    lent = driver.find_element(By.XPATH, f'//tbody/tr[{index}]/td[3]').text # number lent is always in 3rd column
    export['ILL Lent'] = lent     

    if driver.find_element(By.XPATH, f'//tbody/tr[2]/td[{index}]').text == cpl: # assuming the index is the same for loans and borrows
        export['ILL Borrowed'] = driver.find_element(By.XPATH, f'//tbody/tr[3]/td[{index}]').text
    else:
        col_num=3
        while True: 
            html_col=driver.find_element(By.XPATH, f'//tbody/tr[2]/td[{col_num}]')
            if cpl in html_col.text: # looks for the column number of zv052
                break
            col_num += 1
        borrowed = driver.find_element(By.XPATH, f'//tbody/tr[3]/td[{col_num}]').text # number borrowed is always in 3rd row
        export['ILL Borrowed'] = borrowed    
    print("Successfully retrieved interlibrary data")


def append_to_csv(file_name, data): 
    """Appends the collected data into the CIRC-DAILY.csv file as a single row. 
    file_name is the name of the file being edited
    data is the new row of data that will be appended.
    """
    try:
        with open(file_name, 'a', newline = '') as file:
            writer = csv.writer(file)
            writer.writerow(data)
        print('Successfully appended data')
    except Exception:
        print('Could not modify file.')


def get_circ_data(export_data, date, config, file):
    """Calls the functions to get data from Vea API, SierraDNA, 
    and MeL and the append function.
    """
    get_vea(export_data, date, config['Vea'])
    get_sierra(export_data, date, config['SierraDNA'])
    try: # selenium webdriver sometimes doesn't work
        get_mel(export_data, date, config['MeL'])
    except Exception as e:
        print(e)
    if config['Files']['write'].lower() in ['true', 'yes']:
        print("Writing to file...")
        append_to_csv(file, export_data)
    else:
        print(export_data)
        print(r'Read only. To write to file, change "mode" in config.ini to "write".')


def main():
    config = load_config(r'C:\data_collection\collector\config.ini')
    # config = load_config(r'E:\APPLICATIONS\MATERIALS\data_collector\config.ini')
    file = config['Files']['file']
    export_data = create_new_row()
    
    if len(sys.argv) != 1 and sys.argv[1] != 'manual': 
        print("Invalid argument. Either leave blank for auto mode, or enter 'manual'.")
        return -1
    if len(sys.argv) == 1:  # auto mode: appends data from yesterday
        date = 'yesterday'
        get_circ_data(export_data, date, config, file)
        return 0
    if sys.argv[1] == 'manual':  # manual mode: append data from specific date. 
        while True:
            date = input("Enter a date in the format YYYYMMDD or 'q' to quit: ") 
            if date == 'q': 
                return 0
            elif not date.isnumeric() or len(date) != 8:
                print('Invalid entry')
                continue
            else:
                get_circ_data(export_data, date, config, file)

if __name__ == '__main__':
    main()

