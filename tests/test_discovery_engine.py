import os
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

import discovery_engine


class DiscoveryEngineDateTests(unittest.TestCase):
    def test_report_date_uses_asia_shanghai_day_boundary(self):
        utc_time = datetime(2026, 8, 6, 16, 30, tzinfo=timezone.utc)
        with patch.object(discovery_engine, "now_utc", return_value=utc_time):
            with patch.dict(os.environ, {}, clear=False):
                os.environ.pop("DISCOVERY_TIMEZONE", None)
                self.assertEqual(discovery_engine.report_today(), "2026-08-07")


if __name__ == "__main__":
    unittest.main()
