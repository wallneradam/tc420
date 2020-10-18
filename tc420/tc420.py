"""
This is a library to be able to use TC420 LED controller.

This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
from typing import Callable, Tuple, Union
import usb.core
from datetime import datetime, time
from struct import pack, unpack

from threading import Thread


class NoDeviceFoundError(ValueError):
    """ Exception when no TC420 device is found """


class TC420Packet:
    """
    TC420 USB communication packet
    """
    _magic = b"\x55\xaa"
    _command = b"\x00"

    def __init__(self, command=None, payload: Union[bytearray, bytes] = None) -> None:
        if command is None:
            command = self._command

        if payload is None:
            # Create 64 bytes long empty payload
            self.payload = bytearray(
                self._magic + command + b"\x00" * 59 + b"\x0d\x0a")
        else:
            self.payload = bytearray(payload)

        # 1st data position in payload
        self.pointer = 5

    def add_string(self, d: bytes, position: int = None) -> None:
        """
        Add string to the payload at the actual pointer or given position.
        If no position is givem the pointer is used for position and position will be incresed by data length.
        """
        if not d:
            return

        if position is None:  # If no absolute position is specified
            position = self.pointer  # We use our pointer as position
            self.pointer += len(d)  # Increase pointer
        elif position < 0:  # Support for negative position
            position = 64 + position

        assert position + len(d) <= 62

        self.payload[position:position + len(d)] = d

    def add_uchar(self, d: int, position: int = None) -> None:
        """ Add unsigned char to payload """
        self.add_string(pack("!B", d), position)

    def add_ushort(self, d: int, position: int = None) -> None:
        """ Add unsigned short to payload """
        self.add_string(pack("!H", d), position)

    def get_string(self, position=None, length=None):
        """
        Get string from given position or the pointer.
        If position is not given, the pointer is used,
        """
        p = position
        if position is None:
            p = self.pointer
        elif position < 0:
            p = 64 + position

        if length is None:
            length = 56 - position

        if position is None:
            self.pointer += length

        assert p + length <= 62

        return self.payload[p:p+length]

    def get_uchar(self, position: int = None) -> int:
        """ Get uchar from payload """
        return unpack("!B", self.get_string(position=position, length=1))[0]

    def get_ushort(self, position: int = None) -> int:
        """ Get ushort from payload """
        return unpack("!H", self.get_string(position=position, length=2))[0]

    def set_data_len(self, data_len=None):
        """
        Calculates length of data in payload
        This works only if you add data in order without position is specified
        """
        if data_len is None:
            data_len = self.pointer - 5
        assert data_len <= 56
        self.add_ushort(data_len, 3)

    def calc_checksum(self):
        """ Calculates simple checksum by adding all bytes together """
        checksum = 0
        for b in self.payload[:-3]:
            checksum = (checksum + b) & 0xff
        return checksum

    def set_checksum(self, checksum=None):
        """ Set packet checksum. If not specified, it is calculated by calc_checksum """
        if checksum is None:
            checksum = self.calc_checksum()
        self.add_uchar(checksum, -3)

    def __call__(self, update_data_len=True, update_checksum=True) -> bytes:
        """ Returns the final packet to send """
        if update_data_len:
            self.set_data_len()
        if update_checksum:
            self.set_checksum()
        return bytes(self.payload)

    @property
    def magic(self) -> bytes:
        """ Get the magic of the packet """
        return self.get_string(position=0, length=2)

    @property
    def data_len(self) -> int:
        """ Get data length """
        return self.get_ushort(position=3)

    @property
    def command(self) -> int:
        """ Get pacet command """
        return self.get_uchar(position=2)

    @property
    def data(self) -> bytes:
        """ Get packet data """
        return self.get_string(position=5, length=self.data_len)

    @property
    def checksum(self) -> int:
        """ Get packet checksum """
        return self.get_uchar(position=-3)


class TimeSyncPacket(TC420Packet):
    """
    Generates packet for time synchronization
    """
    _command = b"\x11"

    def __init__(self, date: datetime = None) -> None:
        if date is None:
            date = datetime.now()

        super().__init__()

        self.add_ushort(date.year)
        self.add_uchar(date.month)
        self.add_uchar(date.day)
        self.add_uchar(date.hour)
        self.add_uchar(date.minute)
        self.add_uchar(date.second)


class ModeInitPacket(TC420Packet):
    """
    Generates packet for mode initialization
    """
    _command = b"\x12"

    def __init__(self, step_count: int, name: str, bank: int = 0) -> None:
        assert step_count > 1, "Step count must be greater than 1!"
        assert 8 >= len(
            name) > 0, "Name length must be between 1 to 8 characters!"

        super().__init__()

        self.add_uchar(bank)
        self.add_uchar(step_count)
        self.add_string(name.encode('ascii', errors='replace'))


class ModeStepPacket(TC420Packet):
    """
    Generates packet for steps
    """
    _command = b"\x13"

    def __init__(self, step_data: Tuple[Union[datetime, time], int, int, int, int, int]) -> None:
        super().__init__()

        # Set jump flags
        jump_flags = 0
        step_data = list(step_data)
        for b, step in enumerate(step_data[1:]):
            # Negative step value means jump
            if step < 0:
                jump_flags |= 1 << b
                step_data[b + 1] = -step

        self.add_uchar(step_data[0].hour)
        self.add_uchar(step_data[0].minute)
        self.add_uchar(step_data[1])  # CH1
        self.add_uchar(step_data[2])  # CH2
        self.add_uchar(step_data[3])  # CH3
        self.add_uchar(step_data[4])  # CH4
        self.add_uchar(step_data[5])  # CH5
        # The last byte represents the fade/jump flags
        self.add_uchar(jump_flags)


class ModeStepsStopPacket(TC420Packet):
    """
    Generate mode steps end packet
    """
    _command = b"\x01"


class ModeStopPacket(TC420Packet):
    """
    Generate mode steps end packet
    """
    _command = b"\x02"


class ModeClearAllPacket(TC420Packet):
    """
    Generate clear all modes packet
    """
    _command = b"\x03"


class PlayInitPacket(TC420Packet):
    """
    Initialize play mode packet
    """
    _command = b"\x15"

    def __init__(self, name: str) -> None:
        assert 8 >= len(
            name) > 0, "Name length must be between 1 to 8 characters!"

        super().__init__()

        self.add_string(name.encode('ascii', errors='replace'))
        # 0x7f in PLED.exe, but it seems it has no effect
        self.add_ushort(0x7f)


class PlaySetChannels(TC420Packet):
    """
    Set channels in play mode packet
    """
    _command = b"\x16"

    def __init__(self, step_data: Tuple[int, int, int, int, int]) -> None:
        super().__init__()

        self.add_uchar(0xf5)  # It is 0xf5 in PLED.exe, but it seems has no effect et all
        self.add_uchar(step_data[0])  # CH1
        self.add_uchar(step_data[1])  # CH2
        self.add_uchar(step_data[2])  # CH3
        self.add_uchar(step_data[3])  # CH4
        self.add_uchar(step_data[4])  # CH5
        self.add_uchar(0)  # Jump flags not working here


class TC420:
    VENDOR_ID = 0x0888
    PRODUCT_ID = 0x4000

    OK = b"\x00"

    timeout = 5000  # msec

    def __init__(self) -> None:
        # Initialize USB device
        self.dev = usb.core.find(idVendor=TC420.VENDOR_ID, idProduct=TC420.PRODUCT_ID)
        if self.dev is None:
            raise NoDeviceFoundError("TC420 device is not found!")

        # Detach kernel driver (hidraw0)
        if self.dev.is_kernel_driver_active(0):
            self.dev.detach_kernel_driver(0)

        cfg = self.dev[0]
        intf = cfg[(0, 0)]  # Interface - we have only one
        self.in_ep = intf[0]  # Input endpoint
        self.out_ep = intf[1]  # Output endpoint

        self._in_play = False

    def send(self, packet: TC420Packet, check=True) -> bool:
        """ Send a packet to device and wait for answer """
        self.out_ep.write(packet(), timeout=self.timeout)

        res_pkt = None
        if packet._command != ModeStepsStopPacket._command:  # No response for steps end (why?)
            res_pkt = TC420Packet(payload=self.in_ep.read(64, timeout=self.timeout))

        res = True
        if check and res_pkt:
            # The answer packets are not so well designed, they have no magic, no checksum...
            # It seems in case of error they just repeat the sent package from pos 2.
            res = res_pkt.data_len == 1 and res_pkt.data == self.OK

        return res

    def time_sync(self, date: datetime = None) -> bool:
        """
        Send date and time to the device
        :param date: The date and time you want to set on device, if not specified, the time of this computer is used
        """
        return self.send(TimeSyncPacket())

    def mode(self, name: str,
             steps: Tuple[Tuple[datetime, int, int, int, int, int]],
             bank: int = 0,
             step_ready_cb: Callable[[int], None] = None) -> bool:
        """
        Send mode name and steps to device
        :param name: The name of the mode
        :param steps: A tuple of tuple of the step data. One step has a datetime and 5 int in
                      range 0..100 for ch1..ch5. If value is negative, it is a jump (not fade) step.
        :param bank: The bank where to program shuld be placed
        :param step_ready_cb: Step ready callback, it is called after each step is sent.
        """
        assert len(steps) >= 2
        assert name
        assert bank < 64

        # Create mode init packet
        res = self.send(ModeInitPacket(
            name=name, step_count=len(steps), bank=bank))
        assert res, f"Mode '{name}' initialization failed!"
        # Send all steps one by one
        for i, step in enumerate(steps):
            res = self.send(ModeStepPacket(step_data=step))
            assert res, f"Setting step {i+1} in mode '{name}' has been failed!"
            if step_ready_cb is not None:
                step_ready_cb(i + 1)

        # End of steps (no response)
        self.send(ModeStepsStopPacket())

        return True

    def mode_stop(self) -> bool:
        """
        Send node stop to device. It is needed after all modes are sent.
        """
        self._in_play = False
        self._play_step_data = None
        return self.send(ModeStopPacket())

    def mode_clear_all(self) -> bool:
        """
        Send clear all modes command to device
        """
        return self.send(ModeClearAllPacket())

    def play_step(self, step_data: Tuple[int, int, int, int, int]) -> bool:
        """
        Play step if we are in (fast)play mode
        """
        assert self._in_play, "We are not in play mode"
        self._play_step_data = step_data  # It is used in playing thread
        return True

    def play(self, name: str,
             callback: Callable[[], Union[None, Tuple[int, int, int, int, int]]] = None) -> bool:
        """
        Switch to play mode, which is good to try different color level combinations

        When switch is done, the callback is called, where you can return with a tuple containig
        values for CH1..CH5.
        """
        assert name

        res = self.send(PlayInitPacket(name))
        assert res, "Switching to play mode was unsuccessfull!"

        self._play_step_data = None
        self._in_play = True

        def playing_thread():
            """
            Continuously send actual step data for fast playing to keep it alive

            This actually works much better than in PLED.exe. That does not wait for device answer,
            just sends the same again and again like crazy. The device just sending back a lot of errors.
            """
            try:
                while self._in_play:
                    # Send the actual step data
                    if self._play_step_data is not None:
                        self.send(PlaySetChannels(step_data=self._play_step_data))
            except KeyboardInterrupt:
                pass

        # Start playing thread
        t = Thread(target=playing_thread, daemon=True)
        t.start()

        if callback:
            # We call the callback until it returns with None
            while True:
                play_step_data = callback()
                if play_step_data is None:
                    break

                self.play_step(play_step_data)

        return res


if __name__ == "__main__":
    print("This is a function library, it is not for execution.")
