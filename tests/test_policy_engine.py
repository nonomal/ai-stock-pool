from __future__ import annotations

import time
import unittest

from policy_engine import (
    build_pressure_breakdown,
    build_scenario_matrix,
    classify_event_phase,
    compute_crowding_score,
    parse_analyst_page,
)


class PolicyIntelligenceTests(unittest.TestCase):
    def test_parse_analyst_page_extracts_consensus_and_revisions(self) -> None:
        epoch = int(time.time())
        fixture = (
            'targetMeanPrice\\":{\\"raw\\":200.0,\\"fmt\\":\\"200.00\\"},'
            'recommendationMean\\":{\\"raw\\":1.5},'
            'recommendationKey\\":\\"strong_buy\\",'
            'numberOfAnalystOpinions\\":{\\"raw\\":20},'
            'recommendationTrend\\":{\\"trend\\":['
            '{\\"period\\":\\"0m\\",\\"strongBuy\\":8,\\"buy\\":9,\\"hold\\":3,\\"sell\\":0,\\"strongSell\\":0},'
            '{\\"period\\":\\"-3m\\",\\"strongBuy\\":7,\\"buy\\":9,\\"hold\\":4,\\"sell\\":0,\\"strongSell\\":0}]},'
            'upgradeDowngradeHistory\\":{\\"history\\":['
            f'{{\\"epochGradeDate\\":{epoch},\\"firm\\":\\"Example\\",\\"action\\":\\"main\\",'
            '\\"priceTargetAction\\":\\"Raises\\",\\"currentPriceTarget\\":200.0}]}'
        )
        parsed = parse_analyst_page(fixture)
        self.assertEqual(parsed["targetMean"], 200.0)
        self.assertEqual(parsed["analystCount"], 20)
        self.assertEqual(len(parsed["trend"]), 2)
        self.assertEqual(parsed["targetActions"]["raises"], 1)

    def test_crowding_requires_multiple_confirming_signals(self) -> None:
        analyst = {
            "targetMean": 150.0,
            "analystCount": 20,
            "trend": [
                {"period": "0m", "strongBuy": 8, "buy": 10, "hold": 2, "sell": 0, "strongSell": 0},
                {"period": "-3m", "strongBuy": 8, "buy": 9, "hold": 3, "sell": 0, "strongSell": 0},
            ],
            "targetActions": {"raises": 5, "cuts": 0},
        }
        result = compute_crowding_score(analyst, 100.0, -8.0, -12.0, -18.0)
        self.assertGreaterEqual(result["score"], 60)
        self.assertGreaterEqual(len(result["evidence"]), 2)
        self.assertIn(result["zone"], {"crowded", "distribution_risk"})

        price_still_strong = compute_crowding_score(analyst, 100.0, 8.0, 12.0, -4.0)
        self.assertNotEqual(price_still_strong["zone"], "distribution_risk")

    def test_deep_drawdown_with_sticky_consensus_is_distribution_risk(self) -> None:
        analyst = {
            "targetMean": 168.7,
            "analystCount": 43,
            "trend": [
                {"period": "0m", "strongBuy": 20, "buy": 18, "hold": 5, "sell": 0, "strongSell": 0},
                {"period": "-3m", "strongBuy": 19, "buy": 19, "hold": 5, "sell": 0, "strongSell": 0},
            ],
            "targetActions": {"raises": 21, "cuts": 0},
        }
        post_earnings_divergence = compute_crowding_score(
            analyst,
            current_price=100.0,
            return_5d=9.0,
            return_20d=-4.7,
            drawdown_3m=-26.3,
        )
        self.assertEqual(post_earnings_divergence["zone"], "distribution_risk")
        self.assertIn("股价走弱但评级尚未松动", post_earnings_divergence["evidence"])

        strong_price_confirmation = compute_crowding_score(
            analyst,
            current_price=100.0,
            return_5d=6.9,
            return_20d=7.0,
            drawdown_3m=-10.6,
        )
        self.assertNotEqual(strong_price_confirmation["zone"], "distribution_risk")

    def test_pressure_breakdown_and_scenario_are_independent(self) -> None:
        drivers = [
            {"id": "approval", "pressureScore": 80},
            {"id": "ust10y", "pressureScore": 60},
            {"id": "move", "pressureScore": 70},
            {"id": "spx", "pressureScore": 50},
            {"id": "vix", "pressureScore": 80},
            {"id": "inflation", "pressureScore": 55},
        ]
        breakdown = build_pressure_breakdown(drivers)
        self.assertEqual(len(breakdown), 4)
        matrix = build_scenario_matrix(65, 72)
        self.assertEqual(matrix["current"]["id"], "policy_high_crowding_high")

    def test_event_phase_classification(self) -> None:
        self.assertEqual(classify_event_phase("Tariffs delayed as talks resume"), "softening")
        self.assertEqual(classify_event_phase("New sanctions imposed after threat"), "escalation")
        self.assertEqual(classify_event_phase("Final rule takes effect today"), "execution")


if __name__ == "__main__":
    unittest.main()
