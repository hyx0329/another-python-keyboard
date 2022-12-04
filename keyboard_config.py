# N-key roll over
# if False, use legacy 6-key roll over mode over usb
NKRO = True

# USB storage mode
# 0 = default, no action, that's read-write for host
# 1 = read-only for host
# 2 = hide usb storage
USB_STORAGE_MODE = 0

# keyboard timing, in millisecond
# TIME_TAP_THRESH: tap keys held longer than this will trigger their "hold" action
# TIME_TAP_DELAY: tap keys followed by a key event within this delay will trigger their "tap" action
#  press    delay     thresh
#  |        ^         ^
#  v   1    |    2    |    3
# ----------+---------+---------> t
# 1: any key action will trigger `tap`
# 2: any `pressed` action will trigger `hold`, any `release` action will trigger `tap`
# 3: `hold` is triggered
TIME_TAP_THRESH = 170
TIME_TAP_DELAY = 87

# verbosity
VERBOSE = False

