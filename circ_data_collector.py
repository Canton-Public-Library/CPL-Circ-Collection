from datetime import date, datetime, timedelta
import requests
import json
import csv
import psycopg2
import pandas as pd
import os
import sys 
from selenium import webdriver 
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
import configparser

# This script retrieves previous-day data from the SenSource Vea API, the SierraDNA database, and the innopac millennium table and appends it to a csv file.
# There is an optional manual mode that allows users to enter custom dates. This can be accessed by adding "manual" as a command-line argument.
# The clean_upload_append.bat file runs this script at 12:15 AM every day. 
# To properly run this file, there needs to be a config.ini file in the same directory. 

def create_new_row(file):
    """Returns a Pandas series to store the data in a single row
    Args: file- the file which data will be appended to
    """
    data = pd.Series(index = ['Id', 'Date', 'DoorCount', 'CheckedOut', 'TotalSelfCheck', 'DeskCheckOut', 
                            'Renewed', 'TotalCheckedIn', 'TotalCheckedOutReporting', 'Holds', 'New Patrons', 
                            'New Canton Patrons', 'CurbAppt', 'ILL Lent', 'ILL Borrowed', 'Day of Week', 
                            'Month', 'Year', 'Day', 'Day of Week Index', 'Comments'], dtype = 'object')

    data=data.where(pd.notnull(data), None) # Convert all NaN values to None (shows up as blank instead of 'NaN' on CSV files)

    with open(file, 'r') as csv_file:
        id = int(csv_file.readlines()[-1].split(',')[0]) + 1 # get id of appending row in csv file
    data['Id'] = id
    
    return data


def config(section):
    """Returns requested section from config file
    Args: section- specific section from the config file
    """
    config = configparser.ConfigParser()
    # config.read(r'C:\data_collection\collector\config.ini')
    config.read(r'E:\APPLICATIONS\MATERIALS\data_collector\config.ini')
    return config[section]


def get_token():
    """Returns an access token from SenSource."""
    login_info = config('Vea')

    url = login_info['auth_url']
    client_id = login_info['client_id']
    client_secret = login_info['client_secret']
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
    Args: raw_data- dictionary containing Vea API data
    Returns: door count int
    """
    doorcount = data['sumins']
    return doorcount


def get_vea(export, date):
    """Retrieves data from Vea API
    Args: date- specifies which date to get data from. Default is 'yesterday'
    Returns: dictionary containing results
    """
    url = config('Vea')['url']
    
    authtoken = get_token() #access token value
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


def get_sierra(export, mode):
    """Connects to the Sierra database and collects circulation data
    Args: mode- the date mode to query. Either yesterday or custom date.
    Returns: circulation data as a tuple object.
    """
    login_info = config('SierraDNA')
    
    conn = psycopg2.connect(
        database = login_info['database'],
        host = login_info['host'],
        user = login_info['user'],
        password = login_info['password'],
        port = login_info['port']
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


def get_ill(export, date):
    """Retrieves data on interlibrary loans and borrowing from innopac millennium website
    Args: export- the data row that will be appended; date- because the site does not 
    support specific dates, "manual" mode on this will not work.
    """ 
    if date != 'yesterday': 
        export['Comments'] = 'manual entry required for ILL lent and ILL borrowed'
        return

    info = config('Innopac') # get config info 
    url = info['url'] 
    cpl = info['code'] # get library code

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
    Args: file_name- the name of the file being edited; data- a list 
    representing a single row of data that will be appended
    """
    try:
        with open(file_name, 'a', newline = '') as file:
            writer = csv.writer(file)
            writer.writerow(data)
        print('Successfully appended data')
    except Exception:
        print('Could not modify file.')


def get_circ_data(export_data, date, file):
    """Calls the functions to get data from Vea API, SierraDNA, 
    and Innopac Millennium and the append function
    """
    get_vea(export_data, date)
    get_sierra(export_data, date)
    try: # selenium webdriver sometimes doesn't work
        get_ill(export_data, date)
    except Exception as e:
        print(e)
    if config('Files')['write'].lower() in ['true', 'yes']:
        append_to_csv(file, export_data)
    else:
        print(export_data)
        print(r'Read only. To write to file, change "mode" in config.ini to "write".')


def main():
    file = config('Files')['file']
    export_data = create_new_row(file)
    
    if len(sys.argv) != 1 and sys.argv[1] != 'manual': 
        print("Invalid argument. Either leave blank for auto mode, or enter 'manual'.")
        return -1
    if len(sys.argv) == 1:  # auto mode: appends data from yesterday
        date = 'yesterday'
        get_circ_data(export_data, date, file)
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
                get_circ_data(export_data, date, file)

if __name__ == '__main__':
    main()

