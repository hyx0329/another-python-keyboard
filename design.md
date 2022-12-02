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


## How to add a custom board

implement the hardware module with the following listed APIs:

- get_all_tasks() -> List[asyncio.Task]
    - generate all tasks to run, by the `asyncio.gather`
- get_keys() -> int
    - generate key events and return events count
- key_name(key_id) -> str
    - turn a key_id(on the keymap) to it's name
- key_count -> int
    - property, keyboard key count, used to allocate the memory
- hardware_spec -> int
    - property, spec bitmap
- suspend() -> None
    - put the hardware to a low power state, can be a dummy function
- register_hid_info(hid_info: HIDInfo) -> None
    - register an HIDInfo object, can be a dummy function
- iteration interface(`__iter__`, `__next__`)
    - the main loop will use this to iterate through all key events
    - each event should be discarded after use

