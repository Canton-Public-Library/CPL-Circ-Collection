import pandas as pd
import numpy as np
import os
import sys
from config import load_config

# Cleans and formats the CPL Circ CSV file to be compatible with Shiny Dashboard.
# Adapted from CircDataCleaningFormatting.py

def clean_and_format(file):
    df = pd.read_csv(file) 
    df['Date'] = pd.to_datetime(df['Date'], errors = 'coerce') # Making sure Date is set as a Date/Time variable
    df.iloc[:, 2:15] = df.iloc[:, 2:15].apply(pd.to_numeric, errors = 'coerce')
    df['Day of Week'] = df['Date'].dt.day_name()
    df['Month'] = df['Date'].dt.month_name()
    df['Year'] = pd.DatetimeIndex(df['Date']).year
    df['Day'] = pd.DatetimeIndex(df['Date']).day
    df['Day of Week Index'] = df['Date'].dt.dayofweek
    df.dropna(subset = ['Date'], inplace = True)    
    df = df.filter(['Date','DoorCount','CheckedOut','TotalSelfCheck','DeskCheckOut',
        'Renewed','TotalCheckedIn','TotalCheckedOutReporting','Holds','New Patrons','New Canton Patrons',
        'CurbAppt','ILL Lent','ILL Borrowed','Day of Week','Month','Year','Day','Day of Week Index','Comments'])
    df.sort_values(by = 'Date', inplace = True)
    df.reset_index(drop = True, inplace = True)
    df = df.replace({np.nan: None}) # Convert all NaN values to None (shows up as blank instead of 'NaN' on CSV files)
    return df


def main():
    config = load_config(r'C:\data_collection\collector\config.ini')
    # config = load_config(r'E:\APPLICATIONS\MATERIALS\data_collector\config.ini')
    file = config['Files']['file']
    df = clean_and_format(file)
    os.remove(file) 
    df.to_csv(file)

    print("Data Cleaning and Formatting completed")

if __name__ == '__main__':
    main()
