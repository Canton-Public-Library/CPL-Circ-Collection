# Canton Public Library Circulation Data Collection

## Overview
The circulation data collector retrieves and compiles circulation statistics 
from various sources and publishes them online to be processed and displayed 
by the CPL Streamlit app. 

## Data Files
There are two versions of the file containing all the daily circulation data:
1. **Working data file** `\\cpl-circserv\SHINY\Circ Shiny Dashboard\Data
\CPLCircShinyDashboardData\CPL Circ Data.csv`

  This is the version that the application modifies directly. Awaits cleaning 
  and reformatting before being published to the web server.

  **NOTE**: The working data file must not be opened on any computer while the 
  application is running, or else the new data cannot be appended. 

2.	[**Web server data file**](https://sat.cantonpl.org/shiny/CPL%20Circ%20Data.csv)

  The Streamlit app reads the data from this version. This version is copied from 
  the working version and cannot be modified directly by the application.

## Applications and Files
The directory `E:\APPLICATIONS\MATERIALS` on the cpl-batchops server contains
the following components for automating and collecting data:
1.	**Virtual environment** `\venv` 
  
  Directory containing the virtual environment for running the application. The 
  required Python packages are listed in requirements.txt. 

2.	**Collection script** `\data_collector\circ_data_collector.py`

  Python script that collects data from the previous day from the 3 [data sources](https://github.com/Canton-Public-Library/CPL-Circ-    Collection/blob/main/README.md#data-sources) and appends it to the data file. 

3.	**Cleaning script** `\circ_data_cleaner.py`

  Python script that reformats, sorts, and automatically generates new fields to the data. 

4.	**Configuration file** `\data_collector\config.ini`

  Contains confidential information such as URLs and credentials for database access.
  Currently not contained in repository for security concerns. 

  **NOTE**: for the collection script to append data to the data files, the “write” 
  variable under the [Files] section of the configuration file must be set to True. 

5.	**Configuration Module** `\data_collector\config.py`
  
  Python module containing functions for parsing the config.ini file. Used by both 
  the cleaning and collection script.

6.	**Batch file** `\data_collector\clean_upload_append.bat`
  This file is triggered by the task scheduler every day to activate the virtual 
  environment, execute the cleaning script, upload the data file to the web server, 
  and then execute the collection script. 

The task “Circ Daily,” which executes the batch file, can be found in the 
Task Scheduler application in cpl-batchops. 

## Data Sources
The collection script retrieves the following types of data from 3 different sources:
1.	**SenSource Vea API**: Door Count
2.	**SierraDNA**: Date, Checked Out, Total Self Check, Desk Check Out, Renewed, 
Total Checked In, Total Checked Out Reporting, Holds, New Patrons, New Canton Patrons, 
3.	**Michigan eLibrary (MeL)**: Interlibrary Lent, Interlibrary Borrowed

## Debugging Components
`E:\APPLICATIONS\MATERIALS` contains additional functionalities for debugging purposes:
1.	**Log files** `\Logs`

  When clean_upload_append.bat is executed, all console outputs are saved as log files. 

  **NOTE**: because the collection script collects data from the previous day, each log file
  is named by the date of execution rather than the date from which data is pulled from.
  For example, 20230104.log will indicate whether the collection of data from January 3,
  2023 was successful or not. 

2.	**Manual mode** `\manual.bat`

  Batch file that executes the collection script with an additional argument “manual” 
  which allows the user to append data from a specific date. 

## Full Process
Every morning at 8:00 AM, the task scheduler runs `clean_upload_append.bat`, 
which calls the cleaning script to reformat the working data file, uploads a copy of 
the data file to the web server, and then calls the collection script to append data from 
the previous day onto the working data file. During the day, circulation staff opens the 
working data file to manually enter data fields that cannot be collected automatically. 

**NOTE**: because the data file is published to the web server before the most recent 
data is appended, the most recent data that can be viewed on Streamlit will be 2 days 
before the current date. For example, upon execution of the application on October 20, 2023, 
the data up until October 18 is published and viewable on Streamlit. The working data 
file will contain data for October 19 but it will not be published until the next morning. 
