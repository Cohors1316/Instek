"""requires pyserial"""
from typing import overload, Union, Literal
from instek.types import (
    Volts,
    Amps,
    Ohms,
    Watts,
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


class GPDX303S:
    __port: Serial
    __manufacturer: str
    __model: str
    __version: str
    __serial: str
    __remote: bool = None
    __beep: bool
    __tracking: Literal["Independent", "Series", "Parallel"]

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
        return self.__remote

    @remote.setter
    def remote(self, value: bool) -> None:
        self.__communicate("REMOTE") if value else self.__communicate("LOCAL")
        self.__remote = value

    @property
    def baudrate(self) -> int:
        return self.__port.baudrate

    @baudrate.setter
    def baudrate(self, value: Literal[9600, 57600, 115200]) -> None:
        if value == 9600:
            self.__communicate("BAUD2")
        if value == 57600:
            self.__communicate("BAUD1")
        if value == 115200:
            self.__communicate("BAUD0")
        self.__port.baudrate = value

    @property
    def beep(self) -> bool:
        return self.__beep

    @beep.setter
    def beep(self, value: bool) -> None:
        if value == self.__beep:
            return
        self.__communicate(f"BEEP{int(value)}")
        self.__beep = value

    @property
    def output(self) -> bool:
        return bool(int(self.__communicate("OUT?")))

    @output.setter
    def output(self, value: bool) -> None:
        self.__prechecks("remote")
        self.__communicate(f"OUT{int(value)}")

    @property
    def tracking(self) -> str:
        return self.__tracking

    @tracking.setter
    def tracking(self, value: Literal["Independent", "Series", "Parallel"]) -> None:
        self.__prechecks("remote")
        if value == self.__tracking:
            return
        match value:
            case "Independent":
                self.__communicate("TRACK0")
            case "Series":
                self.__communicate("TRACK1")
            case "Parallel":
                self.__communicate("TRACK2")
        self.__tracking = value

    @property
    def channel_1(self) -> tuple[Volts, Amps]:
        return self.__configed_values(1)

    @channel_1.setter
    def channel_1(
        self, value: Union[Volts, Amps, tuple[Volts, Amps]]
    ) -> None:
        self.__configed_values(1, value)

    @property
    def channel_2(self) -> tuple[Volts, Amps]:
        return self.__configed_values(2)

    @channel_2.setter
    def channel_2(
        self, value: Union[Volts, Amps, tuple[Volts, Amps]]
    ) -> None:
        self.__configed_values(2, value)

    def voltage(self, channel: Literal[1, 2]) -> Volts:
        return Volts(self.__XOUT(channel, "V"))

    def current(self, channel: Literal[1, 2]) -> Amps:
        return Amps(self.__XOUT(channel, "I"))

    def __init__(self, port: Serial, response: str = None) -> None:
        self.__port = port
        if response is None:
            response = self.__communicate("*IDN?")
        if response is None:
            if port.is_open:
                port.close()
            raise Exception("Did not receive response from Supply")
        items = response.split(",")
        self.__manufacturer = items[0].strip()
        self.__model = items[1].strip()
        self.__serial = items[2].split(":")[1].strip()
        self.__version = items[3].strip()
        self.__status()
        if self.__port.is_open:
            self.__port.close()

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
        # 5 is output but I can directly query it
        # 6 and 7 is baudrate, not gonna bother because we're obviously connected
        return mode_1, mode_2

    def __prechecks(self, *args: Literal["remote"]) -> None:
        if "remote" in args and self.remote is False:
            raise Exception("Supply is in local mode")

    @overload
    def __configed_values(self, channel: int) -> tuple[Volts, Amps]:
        ...

    @overload
    def __configed_values(
        self, channel: int, value: Union[Volts, Amps, tuple[Volts, Amps]]
    ) -> None:
        ...

    def __configed_values(
        self,
        channel: int,
        value: Union[Volts, Amps, tuple[Volts, Amps]] = None,
    ) -> Union[tuple[Volts, Amps], None]:
        if value is None:
            voltage = self.__communicate(f"VSET{channel}?").removesuffix("V")
            current = self.__communicate(f"ISET{channel}?").removesuffix("A")
            return Volts(voltage), Amps(current)
        if isinstance(value, tuple):
            voltage, current = value
        else:
            voltage = value if isinstance(value, Volts) else None
            current = value if isinstance(value, Amps) else None
        self.__XSET(channel, "V", voltage)
        self.__XSET(channel, "I", current)

    def __XSET(
        self, channel: int, x: Literal["I", "V"], value: float
    ) -> Union[str, None]:
        if value is None:
            return
        self.__prechecks("remote")
        response = self.__communicate(f"{x}SET{channel}:{value}")
        if "Data out of range" in response:
            raise Exception(f"{x} {value} is out of range")
        if "Command not allowed" in response:
            raise Exception(
                f"Cannot set {x} on {channel} while in {self.__tracking} mode"
            )

    def __XOUT(self, channel: int, x: Literal["I", "V"]) -> float:
        response = self.__communicate(f"{x}OUT{channel}?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        if "Invalid Character" in response:
            raise Exception(f"Channel {channel} does not exist")
        if x == "V":
            return float(response.removesuffix("V"))
        if x == "I":
            return float(response.removesuffix("A"))

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


class GPD3303S(GPDX303S):
    pass


class GPD4303S(GPD3303S):
    @property
    def channel_3(self) -> tuple[Volts, Amps]:
        return self.__configed_values(3)

    @channel_3.setter
    def channel_3(
        self, value: Union[Volts, Amps, tuple[Volts, Amps]]
    ) -> None:
        self.__configed_values(3, value)

    @property
    def channel_4(self) -> tuple[Volts, Amps]:
        return self.__configed_values(4)

    @channel_4.setter
    def channel_4(
        self, value: Union[Volts, Amps, tuple[Volts, Amps]]
    ) -> None:
        self.__configed_values(4, value)

    def voltage(self, channel: Literal[1, 2, 3, 4]) -> Volts:
        return Volts(self.__XOUT(channel, "V"))
    
    def current(self, channel: Literal[1, 2, 3, 4]) -> Amps:
        return Amps(self.__XOUT(channel, "I"))


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
