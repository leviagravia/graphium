from __future__ import annotations
import unittest
from graphium.application.commands import COMMANDS, accelerator_map
from graphium.application.commands import COMMANDS, accelerator_map, command_availability
from graphium.domain.edit_history import EditKind, ReplayOperation
from graphium.application.commands import COMMANDS

class ContractArchitectureTests(unittest.TestCase):

    def test_file_command_surface_and_accelerators_are_exact(self):
        file_commands = [(c.action, c.label, c.accelerator) for c in COMMANDS if c.menu == 'File']
        self.assertEqual(file_commands, [('new', 'New', '<Ctrl>N'), ('open', 'Open…', '<Ctrl>O'), ('open-recent', 'Open Recent', None), ('save', 'Save', '<Ctrl>S'), ('save-as', 'Save As…', '<Ctrl><Shift>S'), ('save-copy', 'Save a Copy…', None), ('save-version-copy', 'Save Version Copy…', None), ('properties', 'Properties…', None), ('page-setup', 'Page Setup…', None), ('print-preview', 'Print Preview', '<Ctrl><Shift>P'), ('print', 'Print…', '<Ctrl>P'), ('quit', 'Quit', '<Ctrl>Q')])
        self.assertEqual(accelerator_map()['print'], '<Ctrl>P')
        self.assertEqual(accelerator_map()['print-preview'], '<Ctrl><Shift>P')
        self.assertNotIn('page-setup', accelerator_map())

    def test_search_commands_are_product_owned_and_exact(self):
        search = [(c.action, c.label, c.accelerator) for c in COMMANDS if c.menu == 'Search']
        self.assertEqual(search, [('find', 'Find…', '<Ctrl>F'), ('find-next', 'Find Next', 'F3'), ('find-previous', 'Find Previous', '<Shift>F3'), ('replace', 'Replace…', '<Ctrl>H'), ('go-to-line', 'Go to Line…', '<Ctrl>G')])

def apply_ops(source: str, operations: tuple[ReplayOperation, ...]) -> str:
    text = source
    for op in operations:
        if op.kind is EditKind.INSERT:
            text = text[:op.offset] + op.text + text[op.offset:]
        else:
            assert text[op.offset:op.offset + len(op.text)] == op.text
            text = text[:op.offset] + text[op.offset + len(op.text):]
    return text

class ArchitectureTests(unittest.TestCase):

    def test_32_command_surface_has_exact_six_transform_actions_and_two_accelerators(self):
        transforms = [c for c in COMMANDS if c.submenu == 'Transform Text']
        self.assertEqual([(c.action, c.label, c.accelerator) for c in transforms], [('uppercase', 'Uppercase', None), ('lowercase', 'Lowercase', None), ('duplicate-line-selection', 'Duplicate Line / Selection', None), ('move-lines-up', 'Move Lines Up', '<Alt>Up'), ('move-lines-down', 'Move Lines Down', '<Alt>Down'), ('trim-trailing-spaces', 'Trim Trailing Spaces', None)])
        amap = accelerator_map()
        self.assertEqual(amap['move-lines-up'], '<Alt>Up')
        self.assertEqual(amap['move-lines-down'], '<Alt>Down')

    def test_33_case_command_availability_tracks_nonempty_selection_only(self):
        off = command_availability(modified=False, has_path=True, can_undo=False, can_redo=False, has_selection=False)
        on = command_availability(modified=False, has_path=True, can_undo=False, can_redo=False, has_selection=True)
        self.assertFalse(off.uppercase)
        self.assertFalse(off.lowercase)
        self.assertTrue(on.uppercase)
        self.assertTrue(on.lowercase)

class CurrentCommandSurfaceTests(unittest.TestCase):

    def test_command_surface_is_classic_and_has_no_format_menu(self):
        actual = {(c.menu, c.action) for c in COMMANDS}
        for pair in {('File', 'new'), ('File', 'open'), ('File', 'save'), ('File', 'save-as'), ('File', 'quit'), ('Edit', 'undo'), ('Edit', 'redo'), ('Edit', 'cut'), ('Edit', 'copy'), ('Edit', 'paste'), ('Edit', 'delete'), ('Edit', 'select-all'), ('Help', 'user-guide'), ('Help', 'keyboard-shortcuts'), ('Help', 'about')}:
            self.assertIn(pair, actual)
        self.assertNotIn('Format', {c.menu for c in COMMANDS})
        self.assertEqual([c.action for c in COMMANDS if c.menu == 'Document'], ['statistics'])
