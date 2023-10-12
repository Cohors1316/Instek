"""requires pyserial"""
from time import sleep
from typing import overload, TypeVar, Union, Literal
from .types import (
    Voltage,
    Current,
    Channel,
    Tracking,
    Mode,
    Common,
    State,
)
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


class Supply:
    __tracking: Tracking
    __output: bool
    __beep: bool
    __serial_port: Serial
    __manufacturer: str
    __model: str
    __serial: str
    __version: str
    __channels: list[Channel]

    @property
    def manufacturer(self) -> str:
        return self.__manufacturer

    @property
    def model(self) -> str:
        return self.__model

    @property
    def serial(self) -> str:
        return self.__serial

    @property
    def version(self) -> str:
        return self.__version

    @property
    def beep(self) -> bool:
        return self.__beep

    @property
    def output(self) -> bool:
        return self.__output

    @property
    def channel(self, number: int) -> Channel:
        return self.__channels[number - 1]

    @beep.setter
    def beep(self, value: Union[bool, int]) -> None:
        response = self.__communicate(f"BEEP{int(value)}") != None
        if response:
            raise Exception("Could not set beep")
        self.__beep = value

    @output.setter
    def output(self, value: bool) -> None:
        response = self.__communicate(f"OUT{int(value)}") != None
        if response:
            raise Exception("Could not set output")
        self.__output = value

    @channel.setter
    def channel(
        self,
        channel: Union[
            Channel,
            tuple[int, Voltage, Current],
            tuple[int, Voltage],
            tuple[int, Current],
        ],
    ):
        if isinstance(channel, tuple):
            number = channel[0]
            voltage = [arg for arg in channel if isinstance(arg, Voltage)]
            voltage = voltage[0] if any(voltage) else None
            current = [arg for arg in channel if isinstance(arg, Current)]
            current = current[0] if any(current) else None
            channel = Channel(number, voltage, current)

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
            response = self.__communicate("*IDN?")
            if "instek" in response.lower():
                print(response)
                response = response.split(",")
                self.__manufacturer = response[0]
                self.__model = response[1]
                self.__serial = response[2].split(":")[1]
                self.__version = response[3][1:]
                state = self.__state()
                self.__tracking = state.tracking
                self.__output = state.output
                self.__beep = state.beep
            else:
                raise Exception(
                    "Either this is not a Supply, or could not connect to Supply"
                )
        except:
            raise Exception(
                "Either this is not a Supply, or could not connect to Supply"
            )

    def __str__(self) -> str:
        return f"{self.model}({self.serial})"

    def __repr__(self) -> str:
        return f"{self.model}({self.serial})"

    def __write_line(self, command: str) -> None:
        self.__serial_port.write(command.encode("ascii") + b"\n")

    def __read_line(self) -> str:
        return self.__serial_port.readline().decode("ascii").strip()

    def __communicate(self, command: str) -> Union[str, None]:
        while not self.__serial_port.is_open:
            self.__serial_port.open()
            sleep(0.01)
        self.__write_line(self.__serial_port, command)
        try:
            response = self.__read_line(self.__serial_port)
        except:
            response = None
        self.__serial_port.close()
        return response

    def __state(self) -> State:
        return State(self.__communicate("STATUS?"))

    def __get_voltage(self, channel: Channel) -> Voltage:
        response = self.__communicate(f"VOUT{channel.number}?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        if "Invalid Character" in response:
            raise Exception(f"Channel {channel.number} does not exist")
        return Voltage(float(response.removesuffix("V")))

    def __set_voltage(self, channel: Channel) -> bool:
        response = self.__communicate(f"VSET{channel.number}:{channel.voltage}")
        if response is not None:
            if "Invalid Character" in response:
                raise Exception(f"Channel {channel.number} does not exist")
            elif "Data out of range" in response:
                raise Exception(f"Voltage {channel.voltage} is out of range")
            elif "Command not allowed" in response:
                raise Exception(
                    f"Cannot set voltage on {channel.number} while in {self.__tracking} mode"
                )
        return response == None

    def __get_current(self, channel: Channel) -> Current:
        response = self.__communicate(f"IOUT{channel.number}?")
        if response is None:
            raise Exception("Did not receive response from Supply")
        if "Invalid Character" in response:
            raise Exception(f"Channel {channel.number} does not exist")
        return Current(float(response.removesuffix("A")))

    def __set_current(self, channel: Channel) -> bool:
        response = self.__communicate(f"ISET{channel.number}:{channel.current}")
        if response is not None:
            if "Invalid Character" in response:
                print(f"Channel {channel.number} does not exist")
            elif "Data out of range" in response:
                print(f"Current {channel.current} is out of range")
            elif "Command not allowed" in response:
                print(
                    f"Cannot set current on {channel.number} while in {self.__tracking} mode"
                )
        return response == None

    @overload
    def get(self, property: type[Mode]) -> Mode:
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

        ...

    @overload
    def set(
        self,
        tracking: Literal[Tracking.Independent],
        *channels: Union[
            Channel,
            tuple[int, Voltage, Current],
            tuple[int, Voltage],
            tuple[int, Current],
        ],
    ) -> None:
        ...

    @overload
    def set(
        self,
        tracking: Literal[Tracking.Series],
        voltage: Voltage = None,
        current: Current = None,
    ) -> None:
        ...

    @overload
    def set(
        self,
        tracking: Literal[Tracking.Parallel],
        voltage: Voltage = None,
        current: Current = None,
    ) -> None:
        ...

    def set(
        self,
        *args,
        tracking: Tracking = None,
        output: Output = None,
        beep: Beep = None,
        voltage: Voltage = None,
        current: Current = None,
        channels=None,
    ) -> None:
        track_arg = [arg for arg in args if isinstance(arg, Tracking)]
        tracking = track_arg[0] if any(track_arg) else tracking

        out_arg = [arg for arg in args if isinstance(arg, Output)]
        output = out_arg[0] if any(out_arg) else output

        if output is not None and output != self.__output and output == Output.Off:
            command(self.__serial_port, f"OUT{output.value}")
            self.__output = output
            return None

        beep_arg = [arg for arg in args if isinstance(arg, Beep)]
        beep = beep_arg[0] if any(beep_arg) else beep

        if beep is not None and beep != self.__beep:
            command(self.__serial_port, f"BEEP{beep.value}")
            self.__beep = beep
            return None

        if tracking is not None and tracking != self.__tracking:
            command(self.__serial_port, f"TRACK{tracking.value}")
            self.__tracking = tracking
            self.__output = Output.Off

        match tracking:
            case Tracking.Independent:
                pass
            case Tracking.Series:
                voltage_arg = [arg for arg in args if isinstance(arg, Voltage)]
                voltage = voltage_arg[0] if any(voltage_arg) else voltage
                if voltage is not None and voltage > Voltage(60):
                    raise Exception("Voltage limit is 60V in series mode")
                if voltage is not None and voltage != self.__channel_1_voltage:
                    set_voltage(self.__serial_port, 1, voltage / 2)
                    self.__channel_1_voltage = voltage / 2
                    self.__channel_2_voltage = voltage / 2
                current_arg = [arg for arg in args if isinstance(arg, Current)]
                current = current_arg[0] if any(current_arg) else current
                if current is not None and current > Current(3):
                    raise Exception("Current limit is 3A in series mode")
                if current is not None and current != self.__channel_1_current:
                    set_current(self.__serial_port, 1, current)
                    self.__channel_1_current = current
                    self.__channel_2_current = Current(3)

            case Tracking.Parallel:
                pass
            case None:
                pass

        pass

    def set(
        self,
        tracking: Tracking,
        voltage: Voltage,
        current: Current,
    ) -> None:
        args = list(args)
        # args.extend(kwargs.values())

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


def get_gpds() -> list[Supply]:
    ports = [port for port in comports() if port.manufacturer == "FTDI"]
    gpds = []
    for port in ports:
        try:
            gpd = Supply(port.name)
            gpds.append(gpd)
        except:
            pass
    return gpds


gpd = get_gpds()[0]
gpd.set(Tracking.Series, Voltage(60), Current(3))
gpd.set(Tracking.Parallel, Voltage(30), Current(6))

gpd.set(Tracking.Independent, [Channel(1, Voltage(12), Current(1))])

gpd.channel = Channel(1, Voltage(12), Current(1))
