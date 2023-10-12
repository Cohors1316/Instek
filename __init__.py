"""requires pyserial"""
from enum import Enum
from time import sleep
from typing import overload, TypeVar, Self
import importlib

try:
    importlib.import_module("pyserial")
except ImportError:
    import subprocess

    subprocess.check_call(["pip", "install", "pyserial"])
from serial import Serial
from serial.tools.list_ports import comports


__all__ = [
    "get_gpds",
    "GPD3303",
    "Voltage",
    "Current",
    "Channel",
    "Beep",
    "Output",
    "Tracking",
    "Mode",
    "Common",
]


T = TypeVar("T")


class UnitBase:
    __value: float

    def __init__(self, value: float = 0):
        self.__value = float(round(value, 3))

    def __str__(self) -> str:
        return f"{self.__value}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__value})"

    def __float__(self) -> float:
        return self.__value

    def __int__(self) -> int:
        return int(self.__value)

    def __eq__(self, other: int | float) -> bool:
        if isinstance(other, self.__class__):
            return self.__value == other.__value
        else:
            return self.__value == other

    def __gt__(self, other: int | float) -> bool:
        if isinstance(other, self.__class__):
            return self.__value > other.__value
        else:
            return self.__value > other

    def __lt__(self, other: int | float) -> bool:
        if isinstance(other, self.__class__):
            return self.__value < other.__value
        else:
            return self.__value < other

    def __add__(self, other: int | float) -> Self:
        if isinstance(other, self.__class__):
            return self.__class__(self.__value + other.__value)
        else:
            return self.__class__(self.__value + other)

    def __sub__(self, other: int | float) -> Self:
        if isinstance(other, self.__class__):
            return self.__class__(self.__value - other.__value)
        else:
            return self.__class__(self.__value - other)

    def __mul__(self, other: int | float) -> Self:
        if isinstance(other, self.__class__):
            return self.__class__(self.__value * other.__value)
        else:
            return self.__class__(self.__value * other)

    def __truediv__(self, other: int | float) -> Self:
        if isinstance(other, self.__class__):
            return self.__class__(self.__value / other.__value)
        else:
            return self.__class__(self.__value / other)

    def __floordiv__(self, other: int | float) -> Self:
        if isinstance(other, self.__class__):
            return self.__class__(self.__value // other.__value)
        else:
            return self.__class__(self.__value // other)


class Voltage(UnitBase):
    pass


class Current(UnitBase):
    pass


class Common:
    pass


class Channel(Enum):
    One = 1
    Two = 2


class Beep(Enum):
    On = 1
    Off = 0


class Output(Enum):
    On = 1
    Off = 0


class Tracking(Enum):
    Independent = 0
    Series = 1
    Parallel = 2


class Mode(Enum):
    ConstantCurrent = 0
    ConstantVoltage = 1


class State:
    channel_1: Mode
    channel_2: Mode
    output: Output
    tracking: Tracking
    beep: Beep

    def __init__(self, response: str):
        self.channel_1 = Mode(int(response[0]))
        self.channel_2 = Mode(int(response[1]))
        tracking = response[2:4]
        if tracking == "01":
            self.tracking = Tracking.Independent
        elif tracking == "11":
            self.tracking = Tracking.Series
        elif tracking == "10":
            self.tracking = Tracking.Parallel
        self.beep = Beep(int(response[4]))
        self.output = Output(int(response[5]))

    def __str__(self) -> str:
        return f"State({self.channel_1}, {self.channel_2}, {self.tracking}, {self.beep}, {self.output})"

    def __repr__(self) -> str:
        return f"State({self.channel_1}, {self.channel_2}, {self.tracking}, {self.beep}, {self.output})"


def write_line(serial_port: Serial, command: str) -> None:
    serial_port.write(command.encode("ascii") + b"\n")


def read_line(serial_port: Serial) -> str:
    return serial_port.readline().decode("ascii").strip()


def command(serial_port: Serial, command: str) -> None:
    while not serial_port.is_open:
        serial_port.open()
        sleep(0.01)
    write_line(serial_port, command)
    serial_port.close()
    sleep(0.07)


def communicate(serial_port: Serial, command: str) -> str:
    while not serial_port.is_open:
        serial_port.open()
        sleep(0.01)
    write_line(serial_port, command)
    response = read_line(serial_port)
    serial_port.close()
    return response


def status(serial_port: Serial) -> State:
    return State(communicate(serial_port, "STATUS?"))


def set_voltage(serial_port: Serial, channel: Channel, voltage: Voltage) -> None:
    command(serial_port, f"VSET{channel.value}:{voltage}")


def set_current(serial_port: Serial, channel: Channel, current: Current) -> None:
    command(serial_port, f"ISET{channel.value}:{current}")


def get_voltage(serial_port: Serial, channel: Channel) -> Voltage:
    return Voltage(
        float(communicate(serial_port, f"VOUT{channel.value}?").removesuffix("V"))
    )


def get_current(serial_port: Serial, channel: Channel) -> Current:
    return Current(
        float(communicate(serial_port, f"IOUT{channel.value}?").removesuffix("A"))
    )


class GPD3303:
    manufacturer: str
    model: str
    serial: str
    version: str
    __channel_1_voltage: Voltage
    __channel_2_voltage: Voltage
    __channel_1_current: Current
    __channel_2_current: Current
    __tracking: Tracking
    __output: Output
    __beep: Beep
    __serial_port: Serial

    def __init__(self, port_name: str):
        self.__serial_port = Serial(
            port=port_name,
            baudrate=9600,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=0.1,
        )
        self.__serial_port.close()
        try:
            response = communicate(self.__serial_port, "*IDN?")
            if "instek" in response.lower():
                print(response)
                response = response.split(",")
                self.manufacturer = response[0]
                self.model = response[1]
                self.serial = response[2].split(":")[1]
                self.version = response[3][1:]
                state = status(self.__serial_port)
                self.__tracking = state.tracking
                self.__output = state.output
                self.__beep = state.beep
                self.__channel_1_voltage = Voltage(
                    float(communicate(self.__serial_port, "VSET1?").removesuffix("V"))
                )
                self.__channel_2_voltage = Voltage(
                    float(communicate(self.__serial_port, "VSET2?").removesuffix("V"))
                )
                self.__channel_1_current = Current(
                    float(communicate(self.__serial_port, "ISET1?").removesuffix("A"))
                )
                self.__channel_2_current = Current(
                    float(communicate(self.__serial_port, "ISET2?").removesuffix("A"))
                )
            else:
                raise Exception(
                    "Either this is not a GPD3303, or could not connect to GPD3303"
                )
        except:
            raise Exception(
                "Either this is not a GPD3303, or could not connect to GPD3303"
            )

    def __str__(self) -> str:
        return f"{self.model}({self.serial})"

    def __repr__(self) -> str:
        return f"{self.model}({self.serial})"

    @overload
    def get(self, property: type[Mode]) -> Mode:
        ...

    @overload
    def get(self, property: type[Beep]) -> Beep:
        ...

    @overload
    def get(self, property: type[Output]) -> Output:
        ...

    @overload
    def get(self, property: type[Voltage]) -> Voltage:
        ...

    @overload
    def get(self, property: type[Current]) -> Current:
        ...

    @overload
    def get(self, property: type[Tracking]) -> Tracking:
        ...

    @overload
    def get(self, channel: Channel, property: type[Mode]) -> Mode:
        ...

    @overload
    def get(self, channel: Channel, property: type[Voltage]) -> Voltage:
        ...

    @overload
    def get(self, channel: Channel, property: type[Current]) -> Current:
        ...

    def get(
        self, *args, **kwargs
    ) -> Voltage | Current | Tracking | Output | Beep | Mode:
        args = list(args)
        args.extend(kwargs.values())

        if any([arg for arg in args if arg == Beep]):
            return self.__beep

        if any([arg for arg in args if arg == Output]):
            return self.__output

        if any([arg for arg in args if arg == Tracking]):
            return self.__tracking

        channel = [arg for arg in args if isinstance(arg, Channel)]
        channel = channel[0] if any(channel) else None

        voltage = any([arg for arg in args if arg == Voltage])
        current = any([arg for arg in args if arg == Current])
        mode = any([arg for arg in args if arg == Mode])

        if not voltage and not current and not mode:
            raise Exception("Must specify Current, Voltage, or Mode")

        match self.__tracking:
            case Tracking.Independent:
                if not channel:
                    raise Exception("Must specify channel while in independent mode")
                if voltage:
                    return get_voltage(self.__serial_port, channel)
                if current:
                    return get_current(self.__serial_port, channel)
                if mode:
                    match channel:
                        case Channel.One:
                            return status(self.__serial_port).channel_1
                        case Channel.Two:
                            return status(self.__serial_port).channel_2

            case Tracking.Series:
                if channel and channel == Channel.Two:
                    raise Exception("Channel 2 not accessible in series mode")
                if voltage:
                    return (
                        get_voltage(self.__serial_port, Channel.One)
                        if any([arg for arg in args if arg == Common])
                        else get_voltage(self.__serial_port, Channel.One) * 2
                    )
                if current:
                    return get_current(self.__serial_port, Channel.One)
                if mode:
                    return status(self.__serial_port).channel_1

            case Tracking.Parallel:
                if channel and channel == Channel.Two:
                    raise Exception("Channel 2 not accessible in parallel mode")
                if voltage:
                    return get_voltage(self.__serial_port, Channel.One)
                if current:
                    return get_current(self.__serial_port, Channel.One) * 2
                if mode:
                    return status(self.__serial_port).channel_1

    @overload
    def set(self, beep: Beep) -> None:
        ...

    @overload
    def set(self, output: Output) -> None:
        ...

    @overload
    def set(self, voltage: Voltage) -> None:
        ...

    @overload
    def set(self, current: Current) -> None:
        ...

    @overload
    def set(self, tracking: Tracking) -> None:
        ...

    @overload
    def set(self, voltage: Voltage, current: Current) -> None:
        ...

    @overload
    def set(self, channel: Channel, voltage: Voltage) -> None:
        ...

    @overload
    def set(self, channel: Channel, current: Current) -> None:
        ...

    @overload
    def set(self, channel: Channel, voltage: Voltage, current: Current) -> None:
        ...

    @overload
    def set(self, tracking: Tracking, voltage: Voltage, current: Current) -> None:
        ...

    def set(self, *args, **kwargs) -> None:
        args = list(args)
        args.extend(kwargs.values())

        tracking = [arg for arg in args if isinstance(arg, Tracking)]
        tracking = tracking[0] if any(tracking) else self.__tracking

        channels = [channel for channel in args if isinstance(channel, Channel)]
        if any(channels):
            ch1_index = args.index(Channel.One) if Channel.One in channels else None
            ch2_index = args.index(Channel.Two) if Channel.Two in channels else None
            if ch1_index is not None:
                end_index = (
                    ch2_index if ch2_index and ch2_index > ch1_index else len(args)
                )
                channel_args = args[ch1_index + 1 : end_index]
                voltages = [
                    voltage for voltage in channel_args if isinstance(voltage, Voltage)
                ]
                voltage1 = voltages[0] if any(voltages) else None
                currents = [
                    current for current in channel_args if isinstance(current, Current)
                ]
                current1 = currents[0] if any(currents) else None
            else:
                voltage1, current1 = None, None

            if ch2_index is not None:
                end_index = (
                    ch1_index if ch1_index and ch1_index > ch2_index else len(args)
                )
                channel_args = args[ch2_index + 1 : end_index]
                voltages = [
                    voltage for voltage in channel_args if isinstance(voltage, Voltage)
                ]
                voltage2 = voltages[0] if any(voltages) else None
                currents = [
                    current for current in channel_args if isinstance(current, Current)
                ]
                current2 = currents[0] if any(currents) else None
            else:
                voltage2, current2 = None, None

        else:
            voltages = [voltage for voltage in args if isinstance(voltage, Voltage)]
            voltage1 = voltages[0] if len(voltages) > 0 else None
            voltage2 = voltages[1] if len(voltages) > 1 else None
            currents = [current for current in args if isinstance(current, Current)]
            current1 = currents[0] if len(currents) > 0 else None
            current2 = currents[1] if len(currents) > 1 else None

        match tracking:
            case Tracking.Independent:
                if (
                    voltage1
                    and voltage1 > Voltage(30)
                    or voltage2
                    and voltage2 > Voltage(30)
                ):
                    raise Exception("Voltage limit is 30V in independent mode")
                if (
                    current1
                    and current1 > Current(3)
                    or current2
                    and current2 > Current(3)
                ):
                    raise Exception("Current limit is 3A in independent mode")
            case Tracking.Series:
                if voltage1 and voltage1 > Voltage(60):
                    raise Exception("Voltage limit is 60V in series mode")
                if voltage2:
                    raise Exception("Cannot set voltage for channel 2 in series mode")
                if current2:
                    raise Exception("Current for channel 2 is always 3A in series mode")
            case Tracking.Parallel:
                if voltage1 and voltage1 > Voltage(30):
                    raise Exception("Voltage limit is 30V in parallel mode")
                if voltage2:
                    raise Exception("Cannot set voltage for channel 2 in parallel mode")
                if current1 and current1 > Current(6):
                    raise Exception("Current limit is 6A in parallel mode")
                if current2:
                    raise Exception("Cannot set current for channel 2 in parallel mode")

        output = [arg for arg in args if isinstance(arg, Output)]
        output = output[0] if any(output) else None

        if tracking != self.__tracking:
            command(self.__serial_port, f"TRACK{tracking.value}")
            self.__tracking = tracking
            self.__output = Output.Off

        if output and output != self.__output and output == Output.Off:
            command(self.__serial_port, f"OUT{output.value}")
            self.__output = output

        match tracking:
            case Tracking.Independent:
                if voltage1 and self.__channel_1_voltage != voltage1:
                    set_voltage(self.__serial_port, Channel.One, voltage1)
                    self.__channel_1_voltage = voltage1
                if voltage2 and self.__channel_2_voltage != voltage2:
                    set_voltage(self.__serial_port, Channel.Two, voltage2)
                    self.__channel_2_voltage = voltage2
                if current1 and self.__channel_1_current != current1:
                    set_current(self.__serial_port, Channel.One, current1)
                    self.__channel_1_current = current1
                if current2 and self.__channel_2_current != current2:
                    set_current(self.__serial_port, Channel.Two, current2)
                    self.__channel_2_current = current2
            case Tracking.Series:
                if voltage1 and self.__channel_1_voltage != voltage1 / 2:
                    set_voltage(self.__serial_port, Channel.One, voltage1 / 2)
                    self.__channel_1_voltage = voltage1 / 2
                    self.__channel_2_voltage = voltage1 / 2
                if current1 and self.__channel_1_current != current1:
                    set_current(self.__serial_port, Channel.One, current1)
                    self.__channel_1_current = current1
                if self.__channel_2_current != Current(3):
                    set_current(self.__serial_port, Channel.Two, Current(3))
                    self.__channel_2_current = Current(3)
            case Tracking.Parallel:
                if voltage1 and self.__channel_1_voltage != voltage1:
                    set_voltage(self.__serial_port, Channel.One, voltage1)
                    self.__channel_1_voltage = voltage1
                if current1 and self.__channel_1_current != current1 / 2:
                    set_current(self.__serial_port, Channel.One, current1 / 2)
                    self.__channel_1_current = current1 / 2

        if output and output != self.__output and output == Output.On:
            command(self.__serial_port, f"OUT{output.value}")
            self.__output = output

        if beep := [arg for arg in args if isinstance(arg, Beep)]:
            if beep[0] != self.__beep:
                command(self.__serial_port, f"BEEP{beep[0].value}")
                self.__beep = beep[0]

    def zero(self) -> None:
        self.set(
            Tracking.Independent,
            Voltage(0),
            Voltage(0),
            Current(0),
            Current(0),
            Output.Off,
            Beep.Off,
        )

    def terminals(self, *args) -> str:
        tracking = [arg for arg in args if isinstance(arg, Tracking)]
        tracking = tracking[0] if any(tracking) else self.__tracking
        match tracking:
            case Tracking.Independent:
                return "(2-) (2+) (G) (1-) (1+) (3-) (3+)"
            case Tracking.Series:
                return (
                    "(1-) ( ) ( ) (C) (1+) (3-) (3+)"
                    if any([arg for arg in args if arg == Common])
                    else "(1-) ( ) ( ) ( ) (1+) (3-) (3+)"
                )
            case Tracking.Parallel:
                return "( ) ( ) ( ) (1-) (1+) (3-) (3+)"


def get_gpds() -> list[GPD3303]:
    ports = [port for port in comports() if port.manufacturer == "FTDI"]
    gpds = []
    for port in ports:
        try:
            gpd = GPD3303(port.name)
            gpds.append(gpd)
        except:
            pass
    return gpds
