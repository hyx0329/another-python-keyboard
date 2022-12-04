# Another Python Keyboard

Based on Makerdiary M60 keyboard. This is a firmware written (mostly) in python.

*Document WIP*

## Introduction

This project is refactored from [Makerdiary's `python-keyboard`](https://github.com/makerdiary/python-keyboard) with following advantages:

- easier to port
- easier to extend
- core code and hardware dependent code decoupled
- NKRO implemented
- can easily switch to different keymaps with macros

and with following limitations:

- no pair key support
- no persistent settings(memory), but should be easy to implement
    - keyboard will not connect to the last connected device after power on
    - the heatmap is reseted on each boot
- no auto profile(auto switch keymaps when using a specific BT ID)

*Since this is mostly a rewrite of `python-keyboard`, I repurposed lots of code to support the hardware or simplify the development.*


## Differences

Actually there's no much difference that end users can aware.

The keymaps are compatible(the code processing the keymaps are the same).

Missing features:

- pair keys
- persistent status(BT ID, heatmap are reseted on each boot)

Changed features:

- macro handlers are coroutines now, you can update yours just to add `async` before `def`

Improved:

- backlight update

## How to install

If you are a M60 keyboard user, I'd suggest to:

- install customized firmware in `circuitpython-firmware-for-m60-keyboard`
- tweak the keyboard configurations in `keyboard_config.py`(or do it later)
- copy file/folder listed below to the FAT drive
  - `boot.py`
  - `code.py`
  - `keyboard_config.py`
  - `nkro_utils.py`
  - `keyboard`
  - `keymaps`
  - `m60_matrix2`
- copy the `lib` folder to the drive, or install the following libraries
  - `adafruit_logging` (unless you manually remove every logging line)
  - `adafruit_ble`
  - `adafruit_ticks`
  - `asyncio`
- restart/reset the hardware
  - run `microcontroller.reset()`

## How to port to a different device

For the moment, read `design.md` and the comments in the source files.

### Hardware Interface

For each board you want to support, you only need to implement a `KeyboardHardware` class with a set of methods, read `design.md` for more details.

3 reference implementations given:

- pure python(`m60_py`)
- using `keypad` module(`m60_keypad`)
  - because `keypad` provides only a blocking method, the backlight is not fully implemented
- using custom `matrix2` module(support a special suspend mode)(`m60_matrix2`)
  - need to use the customized firmware

