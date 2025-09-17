import json
import os
import subprocess
import time
import re
import sys
try:
    import serial
except ImportError:
    print('Need to install pyserial, procedure begins')
    subprocess.check_call(['pip', 'install', 'pyserial'])
    import serial

from contextlib import contextmanager
from datetime import datetime

os.system('')
BETAFLIGHT_COMMANDS = ['dump all', 'diff all', 'vtx', 'vtxtable']

def write_to_file(data:str, path:str):
    with open(path, 'w', encoding='utf-8') as file:
        file.write(data)
    print(f'\033[92mCreated file {path}\033[0m')


class Betaflight_dump():

    RESP_TIMEOUT = 10
    BAUD_RATE = 115200
    QUICK_TIMEOUT = 0.2

    def __init__(self, current_time):
        with open('settings.json', encoding='utf-8') as settings:
            data = json.load(settings)
        self.time = current_time
        self.port = data.get('Port')
        self.path_to_save = data.get('Path_to_save_the_files')
        self.wait_for_port()
        self.board_name = None
        self.make_spec_file()

    @contextmanager
    def cli(self):
        port = serial.Serial(self.port, self.BAUD_RATE)
        self.enter_cli(port)
        yield port
        self.exit_cli(port)

    def wait_for_port(self, wait_time_sec=180, check_interval_sec=1):
        elapsed_time = 0
        while elapsed_time < wait_time_sec:
            try:
                ser = serial.Serial(self.port, timeout=1)
                print(f"\033[92mPort {self.port} is available.\033[0m")
                del ser
                return
            except serial.SerialException:
                if not elapsed_time: print(f"\033[33mPort {self.port} is not available. Please connect the USB to FC. "
                                       f"Waited for {wait_time_sec/60} minutes.\033[0m")
            time.sleep(check_interval_sec)
            elapsed_time += check_interval_sec
        print(f"\033[31mPort {self.port} did not appear after {wait_time_sec // 60} minutes. Exiting.\033[0m")
        sys.exit(1)

    def make_spec_file(self):
        with self.cli() as port:
            ver_from_beta = self._perform_betaflight_cli_command(port, 'version')
        processor = re.search(r'STM32F\d+', ver_from_beta).group()
        beta_version = re.search(r'(\d+\.\d+\.\d+)', ver_from_beta).group()
        manuf = re.search(r'manufacturer_id:\s*([A-Z0-9]+)', ver_from_beta).group(1)
        self.board_name = re.search(r'board_name:\s*([A-Z0-9_]+)', ver_from_beta).group(1)
        spec = {
            'Processor': processor,
            'Betaflight Version': beta_version,
            'Target': self.board_name,
            'Manufacturer': manuf,
            'Board_name': self.board_name,
        }
        self.path_to_save = os.path.join(self.path_to_save, f'{self.board_name}.{self.time}')
        path = self.check_folder_does_exist_and_finish_final_path(f'FC_{self.board_name}_Specification.json')
        if not os.path.exists(path):
            with open(path, 'w') as file:
                json.dump(spec, file, indent=4)
            print(f'\033[92mCreated file {path}\033[0m')
            time.sleep(1)


    def check_folder_does_exist_and_finish_final_path(self, file_name:str):
        if not os.path.exists(self.path_to_save):
            os.makedirs(self.path_to_save)
        return os.path.join(self.path_to_save, file_name)

    def enter_cli(self, port:serial.Serial):
        print('Enter Betaflight CLI')
        port.reset_input_buffer()
        port.write(b'#')  # enter debug
        time.sleep(self.QUICK_TIMEOUT)
        res = port.read(port.in_waiting).decode()
        if 'Entering CLI Mode' in res:
            print('\033[92mBetaflight CLI Mode Activated\033[0m')
        else:
            print('\033[31mBetaflight CLI Mode NOT Activated\033[0m')
        time.sleep(1)

    def _perform_betaflight_cli_command(self, port:serial.Serial,  command:str) -> str:
        response = ''
        counter_no_data = 0
        print(f'Perform command #{command}')
        byte_command = bytes(f'{command}\r', encoding='utf-8')
        port.write(byte_command)
        curr = time.time()
        while counter_no_data < 5 and time.time() - curr < self.RESP_TIMEOUT:
            if port.in_waiting > 0:
                chunk = port.read(64 if port.in_waiting > 64 else port.in_waiting)
                response += chunk.decode('utf-8')
            else:
                counter_no_data += 1
                time.sleep(self.QUICK_TIMEOUT)
        response = response[len(command + '\r\n'):]  # remove command from begin
        return response

    def exit_cli(self, port:serial.Serial):
        port.write(b"exit\r\n")
        time.sleep(1)
        port.reset_output_buffer()
        port.reset_input_buffer()
        port.close()
        self.refresh_port()

    def get_betaflight_cli_by_command(self, command:str):
        path = self.check_folder_does_exist_and_finish_final_path(f'Betaflight_{self.board_name}_{command.replace(' ', '_')}.txt')
        with self.cli() as port:
            response = self._perform_betaflight_cli_command(port, command)
        write_to_file(response, path)

    def refresh_port(self):
        try:
            ser = serial.Serial(self.port, 115200)
            ser.write(b"exit\r\n")
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.close()
            time.sleep(2)
            ser = serial.Serial(self.port, 115200)
            print("Port reconnected. =)")
        except Exception:
            time.sleep(2)
            ser = serial.Serial(self.port, 115200)
            if ser: print("Port reconnected. =)")
        del ser

class STM_dump(Betaflight_dump):
    def __init__(self, curr_time):
        super().__init__(curr_time)
        with open('settings.json', encoding='utf-8') as settings:
            data = json.load(settings)
        self.stm_path = os.path.join(data.get('STM32_Cube_Prog_path'), 'STM32_Programmer_CLI.exe')

    def enable_dfu(self):
        print('Enable DFU Mode')
        time.sleep(1)
        with serial.Serial(self.port, 115200) as port:
            port.write(b'ENTER_DFU\n')
        time.sleep(1)

    def check_dfu(self):
        print('Check the USB DFU device')
        dfu = subprocess.Popen([self.stm_path, '-l', 'usb'], stdout=subprocess.PIPE, encoding='utf-8')
        list_opt = dfu.stdout.readlines()
        dfu_quantity = 0
        dfu_ports = []
        no_device = False
        res = None
        for line in list_opt:
            if 'Total number of available' in line:
                dfu_quantity = int(line.split()[-1])
            elif 'Device Index' in line:
                dfu_ports.append(line.split()[-1])
            elif 'No STM32 device in DFU mode connected' in line:
                no_device = True
                break
        if no_device:
            print('\033[33mNo STM32 device in DFU mode:\n\033[0m')
        elif dfu_quantity and len(dfu_ports) == dfu_quantity:
            if dfu_quantity > 1:
                print(f'Found {dfu_quantity} devices in DFU mode:\n')
                for i in dfu_ports:
                    print(f'Device index: {i}\n')
                res = input('Enter your correct DFU (USB1, USB2...etc): ')
            else:
                print(f'Found {dfu_quantity} device in DFU mode: \033[92m{dfu_ports[0]}\033[0m\n')
                res = dfu_ports[0]
        else:
            print('\033[31mSomething went wrong...\033[0m')
        dfu.terminate()
        dfu.wait()
        return res

    def run(self):
        if self.stm_path == 'STM32_Programmer_CLI.exe': return # skip stm dump if no need
        self.enable_dfu()
        dfu_port = self.check_dfu()
        print('Getting dump from FC')
        for file_format in ['bin', 'hex']:
            if dfu_port:
                file_path = self.check_folder_does_exist_and_finish_final_path(f'fc_{self.board_name}_dump.{file_format}')
                dump = subprocess.Popen([self.stm_path, '-c', f'port={dfu_port}', '-u', '0x08000000 0x100000', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                timeout = time.time() + 60
                while time.time() < timeout:
                    line = dump.stdout.readline()
                    line = line.decode('utf-8', errors='ignore')
                    print(line)
                    if 'Time elapsed during read operation'  in line:
                        break
                print(f'\033[92mYour FC .{file_format} dump was saved here: {file_path}\033[0m\n')
                dump.terminate()
                dump.wait()
            else:
                print('No DFU, No your Dump!')
        if dfu_port: print('\033[92mAll job is Done, please PowerUp your FC for exit from DFU\033[0m')


if __name__ == '__main__':
    time_now = datetime.now().strftime("%d_%m_%y(%H_%M_%S)")
    beta = Betaflight_dump(time_now)
    for command in BETAFLIGHT_COMMANDS:
        beta.get_betaflight_cli_by_command(command)
    stm = STM_dump(time_now)
    stm.run()
    input('Press any Key to exit...')