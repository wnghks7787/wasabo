import os, sys, pathlib, shlex 
import time
import docker

from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_DIR = os.path.dirname(__file__)
TOOLS_DIR = os.path.abspath(os.path.join(BASE_DIR, '../../cms_crawler/docker_compose_builder'))
COMPOSE_FILE_DIR = os.path.join(TOOLS_DIR, 'initial_page_builder/compose_files')
sys.path.insert(0, TOOLS_DIR)

import tools
import logger
import runner

BASE_PORT = 10000
CONTAINER_PORT = 80

DEFAULT_FILE_PATH = os.environ.get("PWD")

MAX_WORKER = 7
MIDDLEWARE = 'cache_break.py'

def docker_compose_down(path, yml_file, check):
    tools.run(f"docker compose -f {path}/{shlex.quote(yml_file)} down > /dev/null 2>&1 || true", check=check)

def docker_compose_up(path, yml_file, check, capture):
    r = tools.run(f"docker compose -f {path}/{shlex.quote(yml_file)} up -d > /dev/null 2>&1 || true", check=check, capture=capture)

    if r.returncode != 0:
        logger.log(f"ERROR run 실패: {yml_file} -> {r.stderr.strip()}")


class Docker_Manager:
    def docker_network_setting(self):
        self.client = docker.from_env()
        self.network = self.client.networks.create("fingerprint")

    def setup_mitmproxy(self, middleware_script):
        command = "mitmdump --ssl-insecure"

        volumes = [f"{os.getcwd()}/certs/:/home/mitmproxy/.mitmproxy"]
        if(middleware_script):
            volumes.append(f"{os.getcwd()}/middleware/{middleware_script}:/home/mitmproxy/script.py")
            command += " -s /home/mitmproxy/script.py"

        container = self.client.containers.run("mitmdump:latest", command,
                                name="mitmproxy",
                                network="fingerprint",
                                volumes=volumes,
                                ports={"8080/tcp" : 8080},
                                extra_hosts={'host.docker.internal': 'host-gateway'},
                                detach=True
                                )
        print("waiting 5 sec...")
        time.sleep(5)
        print("waiting end!!!")

    def clean_up(self):
        if self.container:
            self.container.stop(timeout=5)
            self.container.remove()
        if self.network:
            self.network.remove()

def run_flow(idx, repo, tag):
    suffix = idx
    
    image = f"{repo}:{tag}"
    repo_name = repo.split('/')
    name = f"{tools.sanitize_name(repo_name[-1])}-{tag}"
    yml_file = name + ".yml"
    path = f"{COMPOSE_FILE_DIR}/{tools.sanitize_name(repo_name[-1])}-{tag}"
    host_port = BASE_PORT + suffix

    docker_compose_down(path=path, yml_file=yml_file, check=False)
    docker_compose_up(path=path, yml_file=yml_file, check=False, capture=True)

    url = f"host.docker.internal:{host_port}/"

    # 세팅 완료
    # install page 넘기기
    code = runner.wait_http_ready(url, timeout=30, interval=1, follow_redirects=True, max_redirs=10, treat_redirect_ok=False)
    r = tools.run(f"{os.path.join(TOOLS_DIR, 'initial_page_builder')}/initial_page_builder.sh {repo_name[-1]} {host_port} {tag}", check=False)
    time.sleep(3)

    # # 여기부터 달라짐.
    # # webapp_probe.py 실행
# r = tools.run(f"python webapp_probe.py -m {MIDDLEWARE} --worker-mode --webapp-name guess http://host.docker.internal:{host_port}")
    if host_port >= 10000 and host_port <= 10085:
        r = tools.run(f"python webapp_probe.py -m {MIDDLEWARE} --worker-mode --webapp-name wordpress http://host.docker.internal:{host_port}")
    elif host_port >= 10086 and host_port <= 10198:
        r = tools.run(f"python webapp_probe.py -m {MIDDLEWARE} --worker-mode --webapp-name joomla http://host.docker.internal:{host_port}")
    else:
        r = tools.run(f"python webapp_probe.py -m {MIDDLEWARE} --worker-mode --webapp-name drupal http://host.docker.internal:{host_port}")

    docker_compose_down(path=path, yml_file=yml_file, check=False)
    logger.log("cleanup: docker-compose 정리 완료")
    time.sleep(5)

if __name__ == "__main__":
    REPOs = tools.repo_finder()
    pairs_all = []

    docker_manager = Docker_Manager()
    docker_manager.docker_network_setting()
    docker_manager.setup_mitmproxy(MIDDLEWARE)

    for REPO in REPOs:
        REPO = REPO.strip()
        pairs = tools.docker_images(REPO)

        if not pairs:
            logger.log(f"Image not found: {REPO}")
            continue

        for repo, tag in pairs:
            pairs_all.append((len(pairs_all), repo, tag))

    with ThreadPoolExecutor(max_workers=MAX_WORKER) as executor:
        executor.map(lambda args: run_flow(*args), pairs_all)
    
    docker_manager.clean_up()
