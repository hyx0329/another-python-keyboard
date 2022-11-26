from .default import keymap as default_map
from .default import kb_layer1_function
from .qwerty_mod import keymap as qwerty_map
from .qwerty_mod import keymap_plain as qwerty_map_plain
from .dvorak import keymap as dvorak_map
from .norman import keymap as norman_map


keymaps = {
    'default': default_map,
    'qwerty_mod': qwerty_map,
    'qwerty_plain': qwerty_map_plain,
    'dvorak': dvorak_map,
    'norman': norman_map
}
