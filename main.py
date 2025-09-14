import json
import os
import subprocess
import time
try:
    import serial
except ImportError:
    print('Need to install pyserial, procedure begins')
    subprocess.check_call(['pip', 'install', 'pyserial'])
    import serial


class Betaflight_dump():

    RESP_TIMEOUT = 10
    BAUD_RATE = 115200
    QUICK_TIMEOUT = 0.2

    def __init__(self):
        with open('settings.json', encoding='utf-8') as settings:
            data = json.load(settings)
        self.port = data.get('Port')
        self.path_to_save = data.get('Path_to_save_the_files')

    def check_folder_does_exist_and_finish_final_path(self, file_name:str):
        if not os.path.exists(self.path_to_save):
            os.makedirs(self.path_to_save)
        return os.path.join(self.path_to_save, file_name)

    def write_to_file(self, data:str, path:str):
        with open(path, 'w', encoding='utf-8') as file:
            file.write(data)
        print(f'\033[92mCreated file {path}\033[0m')

    def get_betaflight_cli_by_command(self, command:str):
        path = self.check_folder_does_exist_and_finish_final_path(f'betaflight_{command.replace(' ', '_')}.txt')
        port = serial.Serial(self.port, self.BAUD_RATE)
        response = ''
        counter_no_data = 0
        print('Enter Betaflight CLI')
        port.reset_input_buffer()
        port.write(b'#')    #enter debug
        time.sleep(self.QUICK_TIMEOUT)
        res = port.read(port.in_waiting).decode()
        if 'Entering CLI Mode' in res:
            print('\033[92mBetaflight CLI Mode Activated\033[0m')
        time.sleep(1)
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
        port.write(b"exit\r\n")
        time.sleep(1)
        port.reset_output_buffer()
        port.reset_input_buffer()
        port.close()
        response = response[len(command + '\r\n'):]   #remove command from begin
        self.write_to_file(response, path)
        self.refresh_port()

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
    def __init__(self):
        super().__init__()
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
            print('No STM32 device in DFU mode:\n')
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
            print('Something went wrong...')
        dfu.terminate()
        dfu.wait()
        return res

    def run(self):
        self.enable_dfu()
        dfu_port = self.check_dfu()
        print('Getting dump from FC')
        file_path = self.check_folder_does_exist_and_finish_final_path('fc_dump.bin')
        if dfu_port:
            dump = subprocess.Popen([self.stm_path, '-c', f'port={dfu_port}', '-u', '0x08000000 0x100000', file_path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            timeout = time.time() + 60
            while time.time() < timeout:
                line = dump.stdout.readline()
                line = line.decode('utf-8', errors='ignore')
                print(line)
                if 'Time elapsed during read operation'  in line:
                    break
            print(f'Your FC .bin dump was saved here: {file_path}')
            dump.terminate()
            dump.wait()
            print('\033[92mAll job is Done, please PowerUp your FC for exit from DFU\033[0m')
        else:
            print('No DFU, No your Dump!')


if __name__ == '__main__':
    beta = Betaflight_dump()
    beta.get_betaflight_cli_by_command('dump all')
    beta.get_betaflight_cli_by_command('vtxtable')
    stm = STM_dump()
    stm.run()
    input('Press any Key to exit...')