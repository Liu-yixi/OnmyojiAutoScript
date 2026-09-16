import unittest
from unittest.mock import Mock

from tasks.ActivityShikigami.script_task import ScriptTask


class ActivityResourcesTest(unittest.TestCase):
    def test_ap_requires_both_stamina_and_event_item(self):
        for stamina, items, expected in ((5, 100, False), (6, 0, False), (6, 1, True), (150000, 1964, True)):
            with self.subTest(stamina=stamina, items=items):
                task = Mock()
                task.climb_type = 'ap'
                task.wait_until_appear.return_value = True
                task.O_REMAIN_AP.ocr.return_value = stamina
                task.O_REMAIN_AP_ITEM.ocr.return_value = items
                self.assertEqual(ScriptTask.check_tickets_enough(task), expected)


if __name__ == '__main__':
    unittest.main()
