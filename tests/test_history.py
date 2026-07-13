# virtual-ahu/tests/test_history.py — unit tests for trend logging and alarms
from app.bacnet import points
from app.bacnet.objects import PROP_STATUS_FLAGS
from app.bacnet.registry import Registry
from app.history.alarms import AlarmEngine
from app.history.trends import TrendLog


def _fresh_registry() -> Registry:
    reg = Registry()
    points.register_points(reg)
    return reg


def test_trend_log_records_and_queries(tmp_path):
    reg = _fresh_registry()
    log = TrendLog(tmp_path / "trends.db", reg)
    try:
        log.record_sample()
        reg.write_present(*points.ZONE_TEMP, 30.0)
        log.record_sample()

        samples = log.query("analog-input", 1, limit=10)
        assert len(samples) == 2
        assert samples[0]["value"] == 30.0  # newest first
        assert samples[1]["value"] == 22.0  # initial present-value

        # every registered point is sampled
        assert len(log.query("analog-output", 1)) == 2
    finally:
        log.close()


def test_alarm_lifecycle_fire_ack_clear():
    reg = _fresh_registry()
    eng = AlarmEngine(reg, high_limit=26.0, deadband=1.0)
    zone = reg.get(*points.ZONE_TEMP)

    # below the limit: nothing happens
    reg.write_present(*points.ZONE_TEMP, 25.0)
    eng.evaluate()
    assert eng.alarms == []

    # above the limit: alarm fires once, flag raised
    reg.write_present(*points.ZONE_TEMP, 27.0)
    eng.evaluate()
    eng.evaluate()  # still in alarm — must not fire a duplicate
    assert len(eng.alarms) == 1
    alarm = eng.alarms[0]
    assert alarm.state == "active-unacked"
    assert zone.properties[PROP_STATUS_FLAGS]["in-alarm"] is True

    # operator acknowledges
    eng.ack(alarm.id)
    assert alarm.state == "active-acked"

    # inside the deadband (26 > 25.5 > 25): still active, no clear
    reg.write_present(*points.ZONE_TEMP, 25.5)
    eng.evaluate()
    assert alarm.state == "active-acked"

    # below limit - deadband: clears, flag drops
    reg.write_present(*points.ZONE_TEMP, 24.0)
    eng.evaluate()
    assert alarm.state == "cleared"
    assert alarm.cleared_at is not None
    assert zone.properties[PROP_STATUS_FLAGS]["in-alarm"] is False

    # a new excursion raises a NEW alarm
    reg.write_present(*points.ZONE_TEMP, 28.0)
    eng.evaluate()
    assert len(eng.alarms) == 2
    assert eng.alarms[1].state == "active-unacked"