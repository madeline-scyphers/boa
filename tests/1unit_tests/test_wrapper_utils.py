from boa import make_experiment_dir


def test_make_new_exp_dir_when_exp_dir_already_exists(tmp_path):
    exp_name = "test_exp"
    kw = dict(output_dir=tmp_path, experiment_name=exp_name, append_timestamp=False, exist_ok=False)
    dirs = set()
    for _ in range(10):
        exp_dir = make_experiment_dir(**kw)
        dirs.add(exp_dir)
        assert exp_dir.exists()
    assert len(dirs) == 10
