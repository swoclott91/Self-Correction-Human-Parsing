@echo off
echo Activating virtual environment...
call .venv\Scripts\activate
echo.
echo Python environment ready!
echo Current Python: %VIRTUAL_ENV%
echo.
cmd /k 