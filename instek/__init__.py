"""requires pyserial"""
from time import sleep
from typing import overload, TypeVar, Union, Literal
from .types import (
    Voltage,
    Current,
    Mode,
    Common,
)
from serial import Serial
from serial.tools.list_ports import comports


__all__ = [
    "get_gpds",
    "GPD3303",
    "Voltage",
    "Current",
    "Tracking",
    "Common",
]


T = TypeVar("T")


class Channel:
    voltage: Voltage
    current: Current

    def __init__(self, voltage: Voltage = None, current: Current = None):
        self.voltage = voltage
        self.current = current


class GPDX303S:
    __port: Serial
    __manufacturer: str
    __model: str
    __version: str
    __serial: str
    __remote: bool = None
    __baudrate: Literal[9600, 57600, 115200]
    __output: bool
    __beep: bool
    __tracking: Literal["Independent", "Series", "Parallel"]
    __channel_1: Channel = Channel()
    __channel_2: Channel = Channel()

    @property
    def manufacturer(self) -> str:
        return self.__manufacturer

    @property
    def model(self) -> str:
        return self.__model

    @property
    def version(self) -> str:
        return self.__version

    @property
    def serial(self) -> str:
        return self.__serial

    @property
    def remote(self) -> bool:
        if self.__remote is None:
            self.__communicate("REMOTE")
            self.__remote = True
        return self.__remote

    @remote.setter
    def remote(self, value: bool) -> None:
        if value == self.__remote:
            return
        self.__communicate("REMOTE") if value else self.__communicate("LOCAL")
        self.__remote = value
        return

    @property
    def baudrate(self) -> int:
        return self.__baudrate

    @baudrate.setter
    def baudrate(self, value: Literal[9600, 57600, 115200]) -> None:
        if value == self.__baudrate:
            return
        if value == 9600:
            self.__communicate("BAUD2")
        if value == 57600:
            self.__communicate("BAUD1")
        if value == 115200:
            self.__communicate("BAUD0")
        self.__port.baudrate = value
        self.__baudrate = value
        return

    @property
    def output(self) -> bool:
        return self.__output

    @output.setter
    def output(self, value: bool) -> None:
        if value == self.__output:
            return
        self.__communicate(f"OUT{int(value)}")
        self.__output = value
        return

    @property
    def beep(self) -> bool:
        return self.__beep

    @beep.setter
    def beep(self, value: bool) -> None:
        if value == self.__beep:
            return None
        self.__communicate(f"BEEP{int(value)}")
        self.__beep = value
        return

    @property
    def tracking(self) -> str:
        return self.__tracking

    @tracking.setter
    def tracking(self, value: Literal["Independent", "Series", "Parallel"]) -> None:
        if value == self.__tracking:
            return None
        match value:
            case "Independent":
                self.__communicate("TRACK0")
            case "Series":
                self.__communicate("TRACK1")
            case "Parallel":
                self.__communicate("TRACK2")
        self.__output = False
        self.__tracking = value
        return

    @property
    def channel_1(self) -> Channel:
        if self.__channel_1.voltage is None:
            self.__channel_1.voltage = Voltage(self.__XSET(1, "V").removesuffix("V"))
        if self.__channel_1.current is None:
            self.__channel_1.current = Current(self.__XSET(1, "I").removesuffix("A"))
        return self.__channel_1

    @channel_1.setter
    def channel_1(self, value: Union[Voltage, Current]) -> None:
        if isinstance(value, Voltage):
            if value == self.channel_1.voltage:
                return
            self.__XSET(1, "V", value)
            self.__channel_1.voltage = value
        elif isinstance(value, Current):
            if value == self.channel_1.current:
                return
            self.__XSET(1, "I", value)
            self.__channel_1.current = value
        return

    @property
    def channel_2(self) -> Channel:
        if self.__channel_2.voltage is None:
            self.__channel_2.voltage = Voltage(self.__XSET(2, "V").removesuffix("V"))
        if self.__channel_2.current is None:
            self.__channel_2.current = Current(self.__XSET(2, "I").removesuffix("A"))
        return self.__channel_2

    @channel_2.setter
    def channel_2(self, value: Union[Voltage, Current]) -> None:
        if isinstance(value, Voltage):
            if value == self.channel_2.voltage:
                return
            self.__XSET(2, "V", value)
            self.__channel_2.voltage = value
        elif isinstance(value, Current):
            if value == self.channel_2.current:
                return
            self.__XSET(2, "I", value)
            self.__channel_2.current = value
        return

    def __init__(self, port: Serial, response: str = None) -> None:
        self.__port = port
        self.__baudrate = port.baudrate
        if response is None:
            response = self.__communicate("*IDN?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        items = response.split(",")
        self.__manufacturer = items[0].strip()
        self.__model = items[1].strip()
        self.__serial = items[2].split(":")[1].strip()
        self.__version = items[3].strip()
        self.__status()
        if self.__port.is_open:
            self.__port.close()
        return

    def __communicate(self, command: str) -> Union[str, None]:
        while not self.__port.is_open:
            self.__port.open()
        self.__port.write(command.encode("ascii") + b"\n")
        try:
            response = self.__port.readline().decode("ascii").strip()
        except Exception:
            response = None
        self.__port.close()
        return response

    def __status(self) -> tuple[int, int]:
        response = self.__communicate("STATUS?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        mode_1 = int(response[0])
        mode_2 = int(response[1])
        match response[2:4]:
            case "01":
                self.__tracking = "Independent"
            case "11":
                self.__tracking = "Series"
            case "10":
                self.__tracking = "Parallel"
        self.__beep = bool(int(response[4]))
        self.__output = bool(int(response[5]))
        # honestly this is the dumbest bit ever
        # you clearly know the baudrate if you're talking to it
        match response[6:8]:
            case "00":
                self.__baudrate = 115200
            case "01":
                self.__baudrate = 57600
            case "10":
                self.__baudrate = 9600
        return mode_1, mode_2

    @overload
    def __XSET(self, channel: int) -> str:
        ...

    @overload
    def __XSET(self, channel: int, value: float) -> Union[str, None]:
        ...

    def __XSET(
        self, channel: int, parameter: Literal["I", "V"], value: float = None
    ) -> Union[str, None]:
        match value:
            case None:
                response = self.__communicate(f"{parameter}SET{channel}?")
                if response is None:
                    raise Exception("Did not receive response from Supply")
                return response
            case _:
                if not self.__remote:
                    raise Exception("Supply is in local mode")
                response = self.__communicate(f"{parameter}SET{channel}:{value}")
                if response is None:
                    return None
                if "Data out of range" in response:
                    raise Exception(f"{parameter} {value} is out of range")
                if "Command not allowed" in response:
                    raise Exception(
                        f"Cannot set {parameter} on {channel} while in {self.__tracking} mode"
                    )

    def __XOUT(self, channel: int, parameter: Literal["I", "V"]) -> str:
        response = self.__communicate(f"{parameter}OUT{channel}?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        if "Invalid Character" in response:
            raise Exception(f"Channel {channel} does not exist")
        return response

    def __IOUT(self, channel: int) -> float:
        return float(self.__XOUT(channel, "I").removesuffix("A"))

    def __VOUT(self, channel: int) -> float:
        return float(self.__XOUT(channel, "V").removesuffix("V"))

    def __RCL(self, value: Literal[1, 2, 3, 4]) -> None:
        response = self.__communicate(f"RCL{value}")
        if response is not None:
            raise Exception("Could not recall memory")

    def __SAV(self, value: Literal[1, 2, 3, 4]) -> None:
        response = self.__communicate(f"SAV{value}")
        if response is not None:
            raise Exception("Could not save memory")


class GPD2303S(GPDX303S):
    pass


class GPD3303S(GPD2303S):
    pass


class GPD4303S(GPD3303S):
    __channel_3: Channel
    __channel_4: Channel

    @property
    def channel_3(self) -> Channel:
        return self.__channel_3

    @property
    def channel_4(self) -> Channel:
        return self.__channel_4


def __test(port: Serial) -> tuple[bool, str]:
    try:
        port.write(b"*IDN?\n")
        response = port.readline().decode("ascii").strip()
        port.close()
    except Exception:
        port.close()
        return False, None
    if "instek" in response.lower():
        return True, response
    return False, None


def get_devices() -> list[Union[GPD2303S, GPD3303S, GPD4303S]]:
    devices = []
    for port in comports():
        try:
            serial_port = Serial(
                port=port.name,
                baudrate=9600,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=0.01,
            )
            success, response = __test(serial_port)
            if success:
                if "GPD4303S" in response:
                    devices.append(GPD4303S(serial_port, response))
                elif "GPD3303S" in response:
                    devices.append(GPD3303S(serial_port, response))
                elif "GPD2303S" in response:
                    devices.append(GPD2303S(serial_port, response))
        except Exception:
            pass
    return devices
