import logging
import time
import uuid
from pathlib import Path

import docker
from docker.models.containers import Container

from dibench.utils.docker import container_context


def wait_for_docker_daemon(
    container: Container, logger: logging.Logger, timeout: int = 60
):
    start_time = time.time()
    while True:
        exit_code, _ = container.exec_run("docker ps")
        if exit_code == 0:
            logger.info("Docker daemon started.")
            break
        elif time.time() - start_time > timeout:
            raise TimeoutError("Waited too long for Docker daemon to start.")
        else:
            logger.info("Waiting for Docker daemon to start...")
            time.sleep(2)


def preload_images(container: Container, logger: logging.Logger) -> None:
    """Load any *.tar images mounted at /image-cache into the inner Docker daemon,
    then tell act not to re-pull images that are already present."""
    exit_code, out = container.exec_run("sh -c 'ls /image-cache/*.tar 2>/dev/null'")
    if exit_code != 0 or not out.decode().strip():
        return
    for tar in out.decode().split():
        code, o = container.exec_run(f"docker load -i {tar}")
        logger.info(f"docker load {tar}: exit={code} {o.decode()[-300:]}")
    container.exec_run("sh -c 'echo --pull=false >> /root/.actrc'")
    code, o = container.exec_run("docker images")
    logger.info(f"inner images:\n{o.decode()}")


def run_test_ci(
    run_name: str,
    project_root: Path,
    command: str,
    logger: logging.Logger,
    test_output_file: Path,
    timeout: int = 1200,
) -> tuple[bool, str, str]:
    container_name = f"dibench-{run_name}-{str(uuid.uuid4())[:6]}"
    client = docker.from_env(timeout=200)
    with container_context(
        client=client,
        logger=logger,
        project_path=project_root,
        name=container_name,
    ) as container:
        wait_for_docker_daemon(container, logger)
        preload_images(container, logger)
        exit_code, output = container.exec_run("ls")
        logger.info(f"ls /project: {output.decode()}")
        logger.info(f"Running ACT command: {command}")
        exit_code, (stdout, stderr) = container.exec_run(
            cmd=f"timeout {timeout}s {command}", demux=True
        )
        stdout = stdout.decode()
        stderr = stderr.decode()
        test_output_file.write_text(
            f"===== stdout =====\n{stdout}\n===== stderr =====\n{stderr}"
        )

    # a hack to get the result of whether CI passed or failed
    # a workaround but somewhat reliable
    if "🏁  Job failed" in stdout or int(exit_code) == 124:
        # if command times out, it will return 124 with no Job failed message
        logger.error(f"ACT command failed, exit code: {exit_code}")
        return False, stdout, stderr
    if "🏁  Job succeeded" in stdout:
        logger.info(f"ACT command succeeded, exit code: {exit_code}")
        return True, stdout, stderr
    # in case of skipping unsupported platform
    logger.info(f"ACT command failed, has been skipped, exit code: {exit_code}")
    return False, stdout, stderr
