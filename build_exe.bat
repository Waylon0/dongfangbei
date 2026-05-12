@echo off
cd /d "d:\东方杯"
echo Building fault_tracker.exe ...
"D:\my anaconda\python.exe" -m PyInstaller --onefile --windowed --name fault_tracker --add-data "app;app" --add-data "src;src" --add-data "config.py;." --hidden-import streamlit --hidden-import plotly --hidden-import numpy --hidden-import scipy --hidden-import skimage --hidden-import networkx --hidden-import shapely app/main.py
echo Done! Check dist/fault_tracker.exe
pause
