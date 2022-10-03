from kivy.app import App
from kivy.clock import Clock
from kivy.uix.widget import Widget
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.spinner import Spinner
from kivy.uix.popup import Popup
from kivy.properties import ObjectProperty, StringProperty, ColorProperty, ListProperty
from pexpect import fdpexpect
import pexpect
import serial
import serial.tools.list_ports
import threading
from time import sleep, time
import requests
import re

# GLOBALS


class SerCom(Widget):
    # In kivy, properties are used to dynamically update their values in the kv file.
    # Properties can't be declared in lists unless they are, themselves, a list property.
    versions = ['-', '-', '-']
    versions_property = ListProperty()

    # The connect button changes text and color once the bbb is connected.
    connect_button_text = StringProperty('Connect')
    connect_button_color = ObjectProperty((1., 1., 1.))

    # Only the selected version will be highlighted
    v1_button_color = ObjectProperty((1., 1., 1.))
    v2_button_color = ObjectProperty((1., 1., 1.))
    v3_button_color = ObjectProperty((1., 1., 1.))

    v1_button_text = StringProperty(versions[0])
    v2_button_text = StringProperty(versions[1])
    v3_button_text = StringProperty(versions[2])

    # Only the selected OS will be highlighted
    debian_button_color = ObjectProperty((1., 1., 1.))
    angstrom_button_color = ObjectProperty((1., 1., 1.))

    # Some extra properties for configuration
    interfaces = ListProperty([])
    interfaces_color = ObjectProperty((1., 1., 1., 1.))
    version = StringProperty('')
    # The log tab is a regularly updated string, assigned to a kivy label
    logs = StringProperty('')

    progress = StringProperty('0')

    start_flashing = False
    flashing = False

    IP = '192.168.192.1'
    
    status = StringProperty('')
    status_color = ObjectProperty((1., 1., 1., .1))

    def __init__(self):

        self.start_time = time()
        self.popped = False
        # By default, no BBB is connected
        self.connected = False

        # The user needs to select a serial interface over which to communicate
        self.interface = 'N/A'
        self.interfaces = list(port for port, desc,
                               hwid in serial.tools.list_ports.comports())

        # Erase the contents of the serial logfile and then open it, ignoring faulty characters
        open('serial.log', 'w').close()
        self.serialLogs = open('serial.log', errors='ignore')

        # The update method is called every 10 ms. This updates the log screen.
        refresh_time = 0.01
        Clock.schedule_interval(self.update, refresh_time)

        self.ser = None
        self.out = None
        self.os = None

        vs = []

        popup_content = BoxLayout(orientation='vertical', padding=(10))
        popup_content.add_widget(Label(halign='center',
                                       text='Connect the ethernet and TTL cable',
                                       font_name='Montserrat-Regular.ttf'))
        close_button = Button(text='close')
        popup_content.add_widget(close_button)
        self.popup = Popup(title='Warning', content=popup_content,
                           size_hint=(None, None),
                           size=(800, 400))
        close_button.bind(on_release=self.popup.dismiss)

    def connect(self):
        try:
            self.ser = serial.Serial(self.interface, 115200)
            if self.ser.is_open:
                self.connected = True
                # Update the connection button before proceeding
                self.update(None)
                print("Connected")
                self.status = "Connected"

                # Popups are better to manage in kivy file than kv file
                # A popup opens with instructions for the technician to start the netboot
                popup_content = BoxLayout(orientation='vertical', padding=(10))
                popup_content.add_widget(Label(halign='center',
                                               text='Power the BBB off and back on',
                                               font_name='Montserrat-Regular.ttf'))
                close_button = Button(text='close')
                popup_content.add_widget(close_button)
                popup = Popup(title='Warning', content=popup_content,
                              size_hint=(None, None),
                              size=(800, 400))
                close_button.bind(on_release=popup.dismiss)

                # Once dismissed, the program waits for a power toggle in a parallel thread
                popup.bind(
                    on_dismiss=lambda *args: self.thread(self.intercept))
                popup.open()

        except():
            print("Connection failed")
            self.status = "Connection failed"
        self.thread(self.get_images)

    def reconnect(self):
        self.ser = serial.Serial(self.interface, 115200)

    def my_expect(self, pattern):
        found = False
        while not found:
            index = self.installer.expect_exact(
                [pexpect.EOF, pattern], timeout=None)
            if index == 1:
                found = True

    def update(self, dt):
        if self.connected:
            self.connect_button_text = "Connected"
            self.connect_button_color = (0.1176, 0.7019, 0, 1)
            self.logs += self.serialLogs.read()
            if self.ser:
                if self.ser.is_open:
                    self.connected = True
            else:
                self.connected = False
        else:
            self.connect_button_text = "Connect"
            self.connect_button_color = (1., 1., 1.)
        if not self.popped and time()-self.start_time > 1:
            self.popped = True
            self.popup.open()
        self.v1_button_text = self.versions[0]
        self.v2_button_text = self.versions[1]
        self.v3_button_text = self.versions[2]

    def intercept(self):
        try:
            self.out = open('./serial.log', 'wb')
            self.installer = fdpexpect.fdspawn(self.ser)
            self.installer.logfile_read = self.out
            self.installer.delaybeforesend = None
            self.status = "Intercepting autoboot"
            # self.thread(lambda **kwargs:self.send_char(char=' ',duration=3))
            self.my_expect('CPU')
            self.thread(self.send_char(' ', 0.1))
            #self.send_char(char=' ', duration=0.05)
            self.my_expect("=> ")
            self.status = "Autoboot intercepted"
            # intercept_autoboot(self.installer)
        except():
            print("Interception failed")
            self.status = "Interception failed"

    def boot(self):
        if self.connected:
            print('Starting netboot, checking U-Boot version...')
            self.status = "Starting netboot, checking U-Boot version..."
            self.installer.sendline('')
            self.my_expect('=>')
            self.installer.sendline('version')
            self.my_expect('=> ')
            print("> Searching for device tree files...")
            self.status = "Searching for device tree files..."
            self.installer.sendline('run findfdt')
            self.my_expect('=>')
            self.installer.sendline("setenv autoload no; dhcp;")
            self.my_expect('=>')
            print("> Acquiring ip address from DHCP server...")
            self.status = "Acquiring ip address from DHCP server..."
            self.installer.sendline("pxe get")
            self.my_expect('=>')
            self.installer.sendline("pxe boot")
            print("> Booting from the network...")
            self.status = "Booting from network"
            self.installer.expect('run-init: current directory', timeout=None)
            self.send_char(' ', 1)
            sleep(1)
            self.installer.sendline(' ')
            print("> Kernel started. Configuring network interface...")
            self.status = "Kernel started. Configuring network interface..."
            self.installer.sendline('ifconfig eth0 up')
            sleep(1)
            self.installer.expect('(initramfs)', timeout=None)
            self.installer.sendline(
                'ip=$(udhcpc|grep -Eo \'[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+\')')
            sleep(1)
            self.installer.expect('(initramfs)', timeout=None)
            self.thread(lambda *args: self.installer.sendline('ifconfig eth0 $ip'))
            sleep(2)
            self.installer.expect('(initramfs)', timeout=None)
            self.installer.sendline(" ")
            self.installer.expect('(initramfs)', timeout=None)
            self.thread(lambda *args: self.installer.sendline(f'wget -O /dev/mmcblk1 {self.IP}:8000/images/{self.version}/'))
            print("_____________________________________________\n\n\tFlashing network image to EMMC.\n\tThis might take several minutes.\n\tDo not disconnect the device.\n_____________________________________________")
            self.status = "FLASHING TO EMMC\nDO NOT DISCONNECT"
            self.status_color = (.96,.63,0.25,0.35)
            self.installer.expect('(initramfs)', timeout=None)
            self.installer.sendline(" ")
            self.installer.expect('(initramfs)', timeout=None)
            self.installer.sendline(" ")
            self.installer.expect('(initramfs)', timeout=None)
            self.status = "COMPLETE"
            self.status_color = (0.1176, 0.7019, 0)
            # self.installer.expect('(initramfs)')

    def set_version(self, version):
        if version == self.versions[0]:
            self.v1_button_color = (0.1176, 0.7019, 0)
            self.v2_button_color = (1., 1., 1.)
            self.v3_button_color = (1., 1., 1.)

        elif version == self.versions[1]:
            self.v1_button_color = (1., 1., 1.)
            self.v2_button_color = (0.1176, 0.7019, 0)
            self.v3_button_color = (1., 1., 1.)

        elif version == self.versions[2]:
            self.v1_button_color = (1., 1., 1.)
            self.v2_button_color = (1., 1., 1.)
            self.v3_button_color = (0.1176, 0.7019, 0)

        else:
            self.v1_button_color = (1., 1., 1.)
            self.v2_button_color = (1., 1., 1.)
            self.v3_button_color = (1., 1., 1.)
        self.version = version
        print(f'version {version} selected')

    def set_os(self, os):
        if os == 'Debian':
            self.debian_button_color = (0.1176, 0.7019, 0)
            self.angstrom_button_color = (1., 1., 1.)
        elif os == 'Angstrom':
            self.debian_button_color = (1., 1., 1.)
            self.angstrom_button_color = (0.1176, 0.7019, 0)
        self.os = os
        print(f'OS {os} selected')

    def set_interface(self, interface):
        self.interface = interface

    def thread(self, target):
        threading.Thread(target=target).start()

    def abort(self):
        self.installer.sendline('\3')
        self.installer.sendline('\26')

    def send_char(self, char, duration):
        if self.connected:
            flood = True
            start = time()
            while time()-start < duration and flood:
                try:
                    self.installer.send(char)
                    stoptime = time()-start
                except BlockingIOError:
                    print(stoptime)
                    flood = False
        else:
            print("Not connected")

    def get_images(self):
        self.vs = requests.get(f"http://{self.IP}:8000/images/")
        matches = re.findall(
            r"(?<=\"version\":\").*?(?=\")", str(self.vs.content))
        for i in range(len(matches)):
            if matches[i] and i <= 2:
                self.versions[i] = matches[i]
                print(matches[i])
        self.versions_property = self.versions
        print(self.versions)


class Netbooter(Widget):
    serCom = SerCom()

    def __init__(self, **kwargs):
        super(Netbooter, self).__init__(**kwargs)


class NetbooterApp(App):
    def build(self):
        return Netbooter()


if __name__ == '__main__':
    NetbooterApp().run()
