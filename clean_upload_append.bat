@echo off

set CUR_YYYY=%date:~10,4%
set CUR_MM=%date:~4,2%
set CUR_DD=%date:~7,2%
set FILENAME=%CUR_YYYY%%CUR_MM%%CUR_DD%

call E:\APPLICATIONS\MATERIALS\venv\Scripts\activate.bat 
E:\APPLICATIONS\MATERIALS\data_collector\circ_data_cleaner.py > Logs\%FILENAME%.log 2>&1
pscp -pw w38t35t! "\\cpl-circserv\SHINY\Circ Shiny Dashboard\Data\CPLCircShinyDashboardData\CPL Circ Data.csv" "ibranch@sat.cantonpl.org:/var/www/html/shiny" >> Logs\%FILENAME%.log 2>&1
E:\APPLICATIONS\MATERIALS\data_collector\circ_data_collector.py >> Logs\%FILENAME%.log 2>&1
call E:\APPLICATIONS\MATERIALS\venv\Scripts\deactivate.bat