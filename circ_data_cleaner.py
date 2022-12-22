import pandas as pd
import os
import sys
import configparser

# Cleans and formats the CPL Circ CSV file to be compatible with Shiny Dashboard.
# Adapted from CircDataCleaningFormatting.py

def clean_and_format(file):
    df = pd.read_csv(file) # Importing our Data

    df['Date'] = pd.to_datetime(df['Date'], errors = 'coerce') # Making sure Date is set as a Date/Time variable
    df['DoorCount'] = pd.to_numeric(df['DoorCount'],errors = 'coerce')  # be sure when entering data in the excel file before cleaning there are no commas and values are already set to numeric.
    df['CheckedOut'] = pd.to_numeric(df['CheckedOut'],errors = 'coerce') # CheckedOut and DoorCount make sure the columns we create are numeric values.
    df['TotalSelfCheck'] = pd.to_numeric(df['TotalSelfCheck'],errors = 'coerce')               
    df['DeskCheckOut'] = pd.to_numeric(df['DeskCheckOut'],errors = 'coerce')
    df['Renewed'] = pd.to_numeric(df['Renewed'],errors = 'coerce')
    df['TotalCheckedIn'] = pd.to_numeric(df['TotalCheckedIn'],errors = 'coerce')
    df['TotalCheckedOutReporting'] = pd.to_numeric(df['TotalCheckedOutReporting'],errors = 'coerce')
    df['Holds'] = pd.to_numeric(df['Holds'],errors = 'coerce')
    df['New Patrons'] = pd.to_numeric(df['New Patrons'],errors = 'coerce')
    df['New Canton Patrons'] = pd.to_numeric(df['New Canton Patrons'],errors = 'coerce')
    df['CurbAppt'] = pd.to_numeric(df['CurbAppt'],errors = 'coerce')
    df['ILL Lent'] = pd.to_numeric(df['ILL Lent'],errors = 'coerce')
    df['ILL Borrowed'] = pd.to_numeric(df['ILL Borrowed'],errors = 'coerce')
    df['Day of Week'] = df['Date'].dt.day_name()
    df['Month'] = df['Date'].dt.month_name()
    df['Year'] = pd.DatetimeIndex(df['Date']).year
    df['Day'] = pd.DatetimeIndex(df['Date']).day
    df['Day of Week Index'] = df['Date'].dt.dayofweek
    df = df.dropna(subset = ['Date'])

    df = df.filter(['Date','DoorCount','CheckedOut','TotalSelfCheck','DeskCheckOut',
        'Renewed','TotalCheckedIn','TotalCheckedOutReporting','Holds','New Patrons','New Canton Patrons',
        'CurbAppt','ILL Lent','ILL Borrowed','Day of Week','Month','Year','Day','Day of Week Index','Comments'])

    os.remove(file) # Removing the old Dataset since it is now stored within this Python Script
    df.to_csv(file) # Re-writing the Dataset to the same name and same location with updated and cleaned values.

    print("Data Cleaning and Formatting completed") # Letting the user know the script has run and the Data Cleaning is done.

def main():
    config = configparser.ConfigParser()
    config.read(r'E:\APPLICATIONS\MATERIALS\data_collector\config.ini')
    file = config['Files']['file']
    clean_and_format(file)

main()
