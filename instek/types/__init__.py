from enum import Enum
from typing import Self


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


class Channel:
    number: int
    voltage: Voltage
    current: Current

    def __init__(self, number: int, voltage: Voltage = None, current: Current = None):
        self.__channel = number
        self.voltage = voltage
        self.current = current

    def __str__(self) -> str:
        return f"Channel({self.__channel}, {self.voltage}, {self.current})"

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
    channel_4: Mode
    output: bool
    tracking: Tracking
    beep: bool

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
        self.beep = bool(int(response[4]))
        self.output = bool(int(response[5]))

    def __str__(self) -> str:
        return f"State({self.channel_1}, {self.channel_2}, {self.tracking}, {self.beep}, {self.output})"

    def __repr__(self) -> str:
        return f"State({self.channel_1}, {self.channel_2}, {self.tracking}, {self.beep}, {self.output})"
