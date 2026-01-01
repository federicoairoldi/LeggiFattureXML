@echo off

echo #### STARTING DEPLOY ####
cd %~dp0

:: pull new commits form repo
echo PULLING CODE FROM REPO...
git pull

:: update requirements
echo UPDATING ENVIRONMENT...
.venv\Scripts\pip install -r requirements.txt

echo DEPLOY TERMINATED IF ANY ERROR IS PROMPTED SCREENSHOT IT
pause
