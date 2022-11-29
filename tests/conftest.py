import pytest
from testcontainers.compose import DockerCompose


@pytest.fixture(scope="session")
def session(request):
    print("starting docker container")

    compose = DockerCompose(filepath=".", compose_file_name="docker-compose-test.yml", env_file=".env", build=True, pull=True)
    compose.start()
    nn_service_name = compose.get_service_host(service_name="node-norm", port=8080)
    nn_service_port = compose.get_service_port(service_name="node-norm", port=8080)
    nn_url = f"http://{nn_service_name}:{nn_service_port}"
    print(f"nn_url: {nn_url}")
    compose.wait_for(f"{nn_url}")

    callback_service_name = compose.get_service_host(service_name="callback-app", port=8008)
    callback_service_port = compose.get_service_port(service_name="callback-app", port=8008)
    callback_url = f"http://{callback_service_name}:{callback_service_port}"
    print(f"callback_url: {callback_url}")
    compose.wait_for(f"{callback_url}")

    (stdout, stderr, exit_code) = compose.exec_in_container(
        service_name="node-norm",
        command=[
            "python",
            "node_normalizer/load_compendium.py",
            "-c",
            "tests/resources/Cell.txt",
            "-c",
            "tests/resources/Gene.txt",
            "-c",
            "tests/resources/Disease.txt",
            "-r",
            "redis_config.yaml",
        ],
    )
    print(f"stdout: {stdout}, stderr: {stderr}")

    print(f"done building docker containers...ready to proceed")

    def stop():
        print("stopping docker container")
        # stdout, stderr = compose.get_logs()
        # if stderr:
        #     print(f"{stderr}")
        # if stdout:
        #     print(f"{stdout}")
        compose.stop()

    request.addfinalizer(stop)

    return compose, nn_url, callback_url
