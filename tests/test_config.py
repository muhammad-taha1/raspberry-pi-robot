import textwrap

from robotd.config import load


def test_loads_pins(tmp_path):
    path = tmp_path / "robot.toml"
    path.write_text(
        textwrap.dedent(
            """
            [pins]
            led = 24
            motor_in1 = 17
            """
        )
    )

    cfg = load(path)

    assert cfg.pin("led") == 24
    assert cfg.pin("motor_in1") == 17


def test_actual_repo_config_loads():
    """config/robot.toml is the real file the robot deploys with."""
    load("config/robot.toml")
