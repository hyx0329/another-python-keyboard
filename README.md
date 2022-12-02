# Another Python Keyboard

Based on Makerdiary M60 keyboard. This is a firmware written (mostly) in python.

*Document WIP*

## Introduction

This is a project starts from customizing my M60 keyboard. I adjusted the keymap, updated the CircuitPython runtime, and now I'm here, *refactored* the python part. Some weird issue are fixed, and the module becomes very extensible.

The features are similar, the keymaps are compatible.

+ keymaps and hardware_module are device-specific code, implement your own
    + 3 implemention references given,
        - pure python
        - using `keypad` module
            - because `keypad` provides only a blocking method, the backlight is not fully implemented
        - using custom `matrix2` module(support a special suspend mode)

*The original project just doesn't satisfy me. The backlight, the portability, the CircuitPython version, etc.*

*Since this is mostly a rewrite of `python-keyboard`, I repurposed lots of code to support the hardware or simplify the development.*

## Difference to `python-keyboard` by Makerdiary

- decoupled, can be easily ported to another device
- async
    - no blocking delay or wait
    - backlight behaves consistently(no more refresh rate changes)
- NKRO
    - switch between NKRO and 6KRO by changing configuration file (USB only)
- do NOT have persistent settings(e.g. store last bluetooth ID/heatmap)
    - I might implement it but it's not useful to me
    - the heatmap can still be printed to the serial console
- do NOT have pair key support
- do NOT have mouse support (for the moment)

## How to install

If you are a M60 keyboard user, I'd suggest to:

- install my customized firmware in `circuitpython-firmware-for-m60-keyboard`
- tweak the keyboard configurations(or do it later)
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

## How to port to a differernt device

For the moment, read `design.md` and the comments in the source files.

