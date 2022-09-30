import sys
import os
import time

import pytest
import logging
from testcontainers.compose import DockerCompose
from testcontainers.core.docker_client import DockerClient

from node_normalizer.util import LoggingUtil

sys.path.append(os.path.join(os.path.dirname(__file__), "helpers"))

logger = LoggingUtil.init_logging()


@pytest.fixture(scope="session")
def session(request):
    logger.info("starting docker container")

    compose = DockerCompose(filepath=".", compose_file_name="docker-compose-test.yml", env_file=".env", build=True, pull=True)
    compose.start()
    nn_service_name = compose.get_service_host(service_name="r3", port=8080)
    nn_service_port = compose.get_service_port(service_name="r3", port=8080)
    nn_url = f"http://{nn_service_name}:{nn_service_port}"
    logger.info(f"nn_url: {nn_url}")
    compose.wait_for(f"{nn_url}")

    callback_service_name = compose.get_service_host(service_name="callback-app", port=8008)
    callback_service_port = compose.get_service_port(service_name="callback-app", port=8008)
    callback_url = f"http://{callback_service_name}:{callback_service_port}"
    logger.info(f"callback_url: {callback_url}")
    compose.wait_for(f"{callback_url}")

    (stdout, stderr, exit_code) = compose.exec_in_container(service_name="r3", command=["python", "load.py"])
    logger.info(f"stdout: {stdout}, stderr: {stderr}")

    logger.info(f"done building docker containers...ready to proceed")

    def stop():
        logger.info("stopping docker container")
        stdout, stderr = compose.get_logs()
        if stderr:
            logger.error(f"{stderr}")
        if stdout:
            logger.info(f"{stdout}")
        compose.stop()

    request.addfinalizer(stop)

    return compose, nn_url, callback_url
