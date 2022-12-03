# Design

*draft*

## Overall module structure

- Keyboard
    - Keyboard(setup, get key events, propagate to HIDDeviceManager)
        - can be recognized as a kind of middle ware
    - HID
        - HIDDeviceWrapper
            - wrap different HID interface and provide consistent API
        - HIDDeviceWrapperNKRO
            - same as above except adapted to send 16-byte keyboard report
        - HIDDeviceManager
            - manage interface changes and wrap the `HIDDeviceWrapper`
        - HIDInfo
            - a interface for KeyboardHardware to access or set some status data
- KeyboardHardware(Out-of-tree, Device specific, API consistent)
    - provide a set of APIs to scan and process the keys
- Keymaps
    - in company with KeyboardHardware

Keyboard, HIDDeviceManager and KeyboardHardware can have their own coroutines, and the tasks are generated through `get_all_tasks` method.

Keyboard backlight API is not defined yet, I have no idea.

## How to port to a custom keyboard

Just implement the hardware class with the following listed APIs:

- `get_all_tasks() -> List[asyncio.Task]`
    - generate all tasks to run, by the `asyncio.gather`
- `get_keys() -> int`
    - generate key events and return events count
- `key_name(key_id: int) -> str`
    - turn a `key_id`(on the keymap) to it's name
    - actually it's optional, only for logging
- `key_count -> int`
    - property, keyboard key count, used to allocate the memory in advance
- `hardware_spec -> int`
    - property, hardware spec bitmap, see `keyboard/hardware_spec_ids.py`
- `suspend() -> None`
    - put the hardware to a low power state, can be a dummy function
- `register_hid_info(hid_info: HIDInfo) -> None`
    - register an `HIDInfo` object, the hardware can use the object to update status(e.g. backlight)
- iterator interface(`__iter__`, `__next__`)
    - the main loop will use this to iterate through all key events
    - each event should be discarded after use
    - event format (count from 0):
        - bit 7: pressed or not, 0 if pressed, 1 if released
        - bit 6~0: relative key ID (key ID on the keymap)
