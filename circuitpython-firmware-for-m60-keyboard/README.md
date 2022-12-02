# Customized firmware for Makerdiary M60 Keyboard

## Why?

1. Unless using firmware provided by Makerdiary, the keyboard won't properly work without a USB connection, which is unacceptable as it't a bluetooth keyboard.
1. Unless firmware customized, there's no known way to put M60 keyboard to a low power suspend state.
1. The key matrix scanning process implemented in Python is slow, and the bundled `keypad` module provides a blocking API, non of those suits my need.

## Firmware's difference?

Feature | Mine | Makerdiary | Adafruit
:-: | :-: | :-: | :-:
Cpy version | 7.x | 6.x | Since supported 
Operate w/o USB | Y | Y | N
`keypad` module | Y | Y | Y
`matrix` module<sup>1</sup> | N | Y | N
`matrix2` module<sup>2</sup> | Y | N | N
Can suspend(and wake up by key press)? | with `matrix2` | with `matrix` | IDK
Run `python-keyboard` | Y | Y | Y
Run `another-python-keyboard` | Y | Y<sup>3</sup> | Y<sup>3</sup>
Factory reset with button press | N | Y<sup>4</sup> | N

- 1: Makerdiary's key matrix implementation
- 2: My key matrix implementation(ref `matrix` and `keypad`)
- 3: with python-implemented key matrix
- 4: I never used

## How to use the firmware?

- Flash the firmware with a UF2 bootloader(uf2), or
- Flash the firmware with other bootloader or debugger/programmer(hex), or
- Compile the firmware yourself:
    - Clone CircuitPython
    - Checkout 7.3.3 and apply patches
    - Build and flash(see [official guide](https://docs.circuitpython.org/en/latest/BUILDING.html))

