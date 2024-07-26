@echo off
REM Start a new Anaconda prompt with the environment activated and directory changed

%windir%\System32\cmd.exe /K "C:\Users\rashi\anaconda3\Scripts\activate.bat C:\Users\rashi\anaconda3\envs\temoa3 && conda activate temoa3 && cd C:\Users\rashi\ESM_databases\temoa && echo python main.py --config data_files/my_configs/config_sample.toml"
