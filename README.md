# Flight Controller automatic dump script

The script automatically does a full dump from FC, including Betaflight command "dump all", "diff all", "vtx", "vtxtable", and makes a full software backup from STM (.bin, .hex) through STM32CubeProgrammer

## Features

- Possible to use only for the Betaflight dump, without STM32CubeProgrammer (leave an empty string in `'STM32_Cube_Prog_path': ""` in `settings.json`)
- Script uses Betaflight_CLI and STM32CubeProgrammer_CLI
- Script connects directly to the serial port of your FC
- Script creates a folder with the board name, date, and time
- Script creates a separate file for each command from Betaflight
- Makes 2 types of STM firmware (.bin, .hex)

## Requirements

- Python 3.7+
- Required Python packages:
  - `pyserial`    (script should manage it automatically) 
  ```bash
  pip install pyserial
  ```
- STM32CubeProgrammer
  ``` link
  https://www.st.com/en/development-tools/stm32cubeprog.html#get-software
  ```
- All drivers for recognition DFU
  ``` link
  https://www.silabs.com/software-and-tools/usb-to-uart-bridge-vcp-drivers
  https://zadig.akeo.ie/
  https://impulserc.com/pages/downloads
  ```

## Configurtion

  1. **All configurations in `settings.json`**
  2. **Set** the STM32CubeProgrammer/bin directory on your system (For not using STM32, leave empty path)
  3. **Set** path to saving backups
  4. **Set** the Serial COM port of your FC
  Examples:
  ``` json
  {
  "STM32_Cube_Prog_path": "C:\\Program Files\\STM32CubeProgrammer\\bin",
  "Path_to_save_the_files": "C:\\Desktop\\DUMP",
  "Port": "COM30"
  }
  ```

## Running 
  1. Download  `dump_all.py` and `settings.json` or clone the repository
  2. Run from the CMD:
     - Open the folder with `dump_all.py` and `settings.json`
     - In the path field, write `cmd` 
     - In `cmd` write 
        ```bash
        python dump_all.py
        ```
  3. Run from any Python Interpreter
     - Open  `dump_all.py` and press `run`
  4. Wait for all jobs to be done.

## Contributions
  For any suggestions, improvements, issues, errors, report issues, make pull requests, or let me know in Telegram (link in bio) 

## License
This project is licensed under the MIT License.
