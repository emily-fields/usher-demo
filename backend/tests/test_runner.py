import dataclasses

import pytest

from app.pipeline.runner import ToolError, build_command, run_tool


def test_build_command_unwrapped_by_default(settings, tmp_path):
    assert build_command(["usher", "-i", "x"], tmp_path, settings) == ["usher", "-i", "x"]


def test_build_command_wraps_bio_tools_in_docker(settings, tmp_path):
    wrapped = dataclasses.replace(settings, docker_wrap=True)
    cmd = build_command(["usher", "-i", "x"], tmp_path, wrapped)
    assert cmd[:5] == ["docker", "run", "--rm", "--platform", "linux/amd64"]
    assert f"{settings.data_dir}:{settings.data_dir}" in cmd
    assert f"{settings.trees_dir}:{settings.trees_dir}" in cmd
    assert cmd[-4:] == [settings.usher_image, "usher", "-i", "x"]


def test_build_command_never_wraps_usher_to_taxonium(settings, tmp_path):
    wrapped = dataclasses.replace(settings, docker_wrap=True)
    assert build_command(["usher_to_taxonium", "--input", "x"], tmp_path, wrapped)[0] == "usher_to_taxonium"


def test_run_tool_raises_with_last_stderr_line_and_writes_log(settings, tmp_path):
    log = tmp_path / "logs" / "fail.log"
    with pytest.raises(ToolError, match="sh failed: second problem"):
        run_tool(["sh", "-c", "echo first >&2; echo second problem >&2; exit 3"],
                 workdir=tmp_path, settings=settings, timeout=10, log_path=log)
    assert "second problem" in log.read_text()


def test_run_tool_returns_stdout(settings, tmp_path):
    assert run_tool(["sh", "-c", "echo hi"], workdir=tmp_path, settings=settings, timeout=10).strip() == "hi"
