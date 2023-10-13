from enum import Enum
from typing import Self
from decimal import Decimal
from typing import Union
from math import sqrt


__all__ = [
    "Volts",
    "Amps",
    "Ohms",
    "Watts",
    "Mode",
]


class UnitBase:
    __value: Decimal

    def __init__(self, value: Union[Decimal, float, str, int] = 0):
        if not isinstance(value, (Decimal, int, str, float)):
            value = str(value)
        self.__value = value

    def __str__(self) -> str:
        return f"{round(self.__value, 3)}"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.__value})"

    def __float__(self) -> float:
        return self.__value

    def __int__(self) -> int:
        return int(self.__value)

    def __bool__(self) -> bool:
        return bool(self.__value)

    def __hash__(self) -> int:
        return hash(self.__repr__())

    def __abs__(self) -> Self:
        return self.__class__(abs(self.__value))

    def __pow__(self, other: Union[Decimal, int, float, str]) -> Self:
        return self.__class__(self.__value ** self.__class__(other).__value)

    def __eq__(self, other: Union[Decimal, int, float, str]) -> bool:
        if isinstance(other, (Decimal, int, float, str, self.__class__)):
            return self.__value == self.__class__(other).__value
        raise TypeError(f"Cannot compare {self.__class__.__name__} with {type(other)}")

    def __gt__(self, other: Union[Decimal, int, float, str]) -> bool:
        if isinstance(other, (Decimal, int, float, str, self.__class__)):
            return self.__value > self.__class__(other).__value
        raise TypeError(f"Cannot compare {self.__class__.__name__} with {type(other)}")

    def __lt__(self, other: Union[Decimal, int, float, str]) -> bool:
        if isinstance(other, (Decimal, int, float, str, self.__class__)):
            return self.__value < self.__class__(other).__value
        raise TypeError(f"Cannot compare {self.__class__.__name__} with {type(other)}")

    def __add__(self, other: Union[Decimal, int, float, str]) -> Self:
        if isinstance(other, (Decimal, int, float, str, self.__class__)):
            return self.__class__(self.__value + self.__class__(other).__value)
        raise TypeError(f"Cannot add {self.__class__.__name__} with {type(other)}")

    def __sub__(self, other: Union[Decimal, int, float, str]) -> Self:
        if isinstance(other, (Decimal, int, float, str, self.__class__)):
            return self.__class__(self.__value - self.__class__(other).__value)
        raise TypeError(f"Cannot subtract {self.__class__.__name__} with {type(other)}")

    def __mul__(self, other: Union[Decimal, int, float, str]) -> Self:
        return self.__class__(self.__value * self.__class__(other).__value)

    def __truediv__(self, other: Union[Decimal, int, float, str]) -> Self:
        return self.__class__(self.__value / self.__class__(other).__value)

    def __floordiv__(self, other: Union[Decimal, int, float, str]) -> Self:
        return self.__class__(self.__value // self.__class__(other).__value)


def __throw_error(self, other, operation: str) -> None:
    raise TypeError(
        f"Cannot {operation} {self.__class__.__name__} by {other.__class__.__name__}"
    )


class Volts(UnitBase):
    def __mul__(self, other) -> "Watts" | Self:
        if isinstance(other, Amps):
            return Watts(self.__value * other.__value)
        if isinstance(other, (Ohms, Watts)):
            __throw_error(self, other, "multiply")
        return super().__mul__(other)

    def __truediv__(self, other) -> "Amps" | "Ohms" | Self:
        if isinstance(other, Amps):
            return Ohms(self.__value / other.__value)
        if isinstance(other, Ohms):
            return Amps(self.__value / other.__value)
        if isinstance(other, Watts):
            return Ohms((self.__value**2) / other.__value)
        return super().__truediv__(other)


class Amps(UnitBase):
    def __mul__(self, other) -> Volts | "Watts" | Self:
        if isinstance(other, Ohms):
            return Volts(self.__value * other.__value)
        if isinstance(other, Volts):
            return Watts(self.__value * other.__value)
        if isinstance(other, Watts):
            __throw_error(self, other, "multiply")
        return super().__mul__(other)

    def __truediv__(self, other) -> Self:
        if isinstance(other, (Volts, Ohms, Watts)):
            __throw_error(self, other, "divide")
        return super().__truediv__(other)


class Ohms(UnitBase):
    def __mul__(self, other) -> Volts | Self:
        if isinstance(other, Amps):
            return Volts(self.__value * other.__value)
        if isinstance(other, Watts):
            return Volts(sqrt(self.__value / other.__value))
        if isinstance(other, Volts):
            __throw_error(self, other, "multiply")
        return super().__mul__(other)

    def __truediv__(self, other) -> Self:
        if isinstance(other, (Watts, Volts, Amps)):
            __throw_error(self, other, "divide")
        return super().__truediv__(other)


class Watts(UnitBase):
    def __mul__(self, other) -> Volts | Self:
        if isinstance(other, Ohms):
            return Volts(sqrt(self.__value * other.__value))
        if isinstance(other, (Volts, Amps)):
            __throw_error(self, other, "multiply")
        return super().__mul__(other)

    def __truediv__(self, other) -> Amps | Volts | Self:
        if isinstance(other, Volts):
            return Amps(self.__value / other.__value)
        if isinstance(other, Amps):
            return Volts(self.__value / other.__value)
        if isinstance(other, Ohms):
            return Amps(sqrt(self.__value / other.__value))
        return super().__truediv__(other)


class Mode(Enum):
    ConstantCurrent = 0
    ConstantVoltage = 1
