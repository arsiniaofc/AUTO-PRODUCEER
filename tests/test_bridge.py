import unittest
import socket
import time
from backend.fl_studio.bridge import FLStudioBridge


class TestFLStudioBridge(unittest.TestCase):
    def test_bridge_start_and_emergency_stop(self):
        bridge = FLStudioBridge(port=9099)
        res = bridge.start_bridge()
        self.assertEqual(res["status"], "ok")
        self.assertTrue(bridge.status.is_running)

        # Test command
        cmd_res = bridge.send_command("transport_play")
        self.assertEqual(cmd_res["status"], "success")

        # Test emergency stop
        stop_res = bridge.trigger_emergency_stop()
        self.assertEqual(stop_res["status"], "stopped")
        self.assertTrue(bridge.emergency_stop_triggered)

        # Blocked action
        blocked = bridge.send_command("transport_play")
        self.assertEqual(blocked["status"], "error")

        # Reset
        bridge.reset_emergency_stop()
        self.assertFalse(bridge.emergency_stop_triggered)

        bridge.stop_bridge()
        self.assertFalse(bridge.status.is_running)


if __name__ == "__main__":
    unittest.main()
