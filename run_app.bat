@echo off
cd /d "d:\东方杯"
start "" http://localhost:8501
"D:\my anaconda\python.exe" -m streamlit run app/main.py --server.port 8501 --server.address localhost
pause
