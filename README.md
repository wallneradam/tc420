# TC420 LED Controller Python Library and Command Line Interface

TC420 is a LED dimmer/controller mainly used for aquarium lightning. There is an attached software, PLED, you can use for programming it, but it is not very well written, and not good for automation tasks. Also it is Windows only.
You can found more information on its fun (not official) site: https://www.tc420.net/.

I reverse engineered the USB protocol the device uses and wrote this library and CLI tool for making endless possibilities from this device. I successfully implemented all the functions PLED.exe have.

The library is cross platform, works everywhere where [libusb](https://github.com/libusb/libusb) works. But because it is a HID device, and MacOS does not allow to detach kernel drivers of HID devices, on MacOS it is extremely hard to make it work in current form. But I tested on **Windows** and **Linux**, and works fine there. It works on (all kinds of) Raspberry Pi, so it
(Actually there is a python library for HID devices, so theoretically it is possible to rewrite the lib using hidapi, and then it could work on MacOS as well, pull requests are welcome...)

It has a full featured **CLI**, which can act as a reference for the libray. Also you can use it for automation, or just for fun.

## Possibilities / ideas

- You can program your device in shell scripts / batch files, or with Python programs
- You can run immediate scenes, e.g. a sunset or sunrise by a click to attract your guests
- It is possible to access the device remotely by e.g. a Raspberry Pi Zero W
- A web / mobile application can be written to start scenes, or modify program of device (not yet written by myself)
- Different color themes on sunny/rainy/cloudy days, by using online weather sources
- Real sunset and sunrise program every day by using sunset/sunrise database.
- ...

## Install

### Linux

- Install the library:
```bash
pip3 install tc420
```
- Install libusb if not installed. On Raspberry pi it is installed by default.
- Create a *plugdev* group if not exists, it exists by default in all Debian based distros.
- Enable the access of the device by users in plugdev group with an udev rule found here: [99-tc420.rules](https://raw.githubusercontent.com/wallneradam/tc420/main/etc/udev/rules.d/99-tc420.rules).
Put that (by root user) in */etc/udev/rules.d/*, then replug your device.
- Put yourself into the *plugdev* group then relogin:
```bash
sudo adduser your_user_name plugdev
```

### Windows

- Install Python 3.6+ if not installed: https://docs.python.org/3/using/windows.html
- Install the library:
```
pip install tc420
```
- Install latest libusb, which is kinda tricky: [this Stackoverflow answer worked for me](https://stackoverflow.com/questions/33972145/pyusb-on-windows-8-1-no-backend-available-how-to-install-libusb/34720024#34720024)

### From source

This description works without modification on Linux, on Windows, you may need to use `pip` instead of `pip3` and `python` instead of `python3`. And the activate.bat is in the `Scripts` folder inside `venv`.

- Clone package from GitHub:
```
git clone https://github.com/wallneradam/tc420.git
```
- Install virtualenv (globally) if not yet installed:
```
sudo -H pip3 install virtualenv
```
- Create a VirtualEnv inside the cloned directory:
```
virtualenv -p python3 venv
```
- Activate it:
```
./venv/bin/activate
```
- Install package with requirements:
```
pip install -e .
```

Now you have tc420 command in your virtual environment.

## Usage

Both the library and the CLI tool is documented and the source code is commented, so you can find all information inside them.

### CLI

You can have the help of `tc420` command by running:
```
tc420 --help
```
This will only give you brief information about all commands.
You can have full description of every commands by running:
`tc420 [command] --help` e.g.:
```
tc420 mode --help
```

#### Getting started

For checking if everything is working you can sync the clock:
```
tc420 time-sync
```
Or you can run the demo which randomly fades in-out all channels:
```
tc420 demo
```

If something is not working, you probably not installed libusb well, or you need to check if you have permissions to access the device.
