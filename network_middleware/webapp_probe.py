import sys
import os
import os.path
import json
import time
import importlib
import shutil
import docker
import argparse
import logging

TESTS_DIR = 'testbeds'

class Driver:

    def __init__(self, middleware_script=None):
        self.containers = []
        self.middleware_container = None
        self.docker_client = docker.from_env()
        self.network = self.docker_client.networks.create("fingerprint")

        # Setup mitmproxy with chosen middleware script
        self.setup_mitmproxy(middleware_script)

    def clean_up(self):
        for container in self.containers:
            try:
                container.stop(timeout=5)
                container.remove()
            except Exception as e:
                logging.error(e)
                pass
        try:
            self.network.remove()
        except Exception as e:
            logging.error(e)
            pass
        self.containers = []
        self.middleware_container = None

    def setup_mitmproxy(self, middleware_script):
        command = "mitmdump --ssl-insecure"

        volumes = [f"{os.getcwd()}/certs/:/home/mitmproxy/.mitmproxy"]
        if(middleware_script):
            volumes.append(f"{os.getcwd()}/middleware/{middleware_script}:/home/mitmproxy/script.py")
            command += " -s /home/mitmproxy/script.py"

        container = self.docker_client.containers.run("mitmdump:latest", command,
                                name="mitmproxy",
                                network="fingerprint",
                                volumes=volumes,
                                ports={"8080/tcp" : 8080},
                                detach=True,
                                extra_hosts={'host.docker.internal': 'host-gateway'},
                                # remove=True,
                                )
        self.containers.append(container)
        self.middleware_container = container
        time.sleep(5)

    def run_test(self, url, webapp_name, testbed):
        try:
            # Import the specified testbed
            testbed_module = importlib.import_module('testbeds.' + testbed)
            testbed_class = getattr(testbed_module, 'Testbed')
            testbed = testbed_class()
            testbed.run_test(webapp_name, url)
        except Exception as e:
            logging.error(e)

def run_test_workermode(url, webapp_name, testbed):
    try:
        testbed_module = importlib.import_module('testbeds.' + testbed)
        testbed_class = getattr(testbed_module, 'Testbed')
        testbed = testbed_class()
        testbed.run_test(webapp_name, url)
    except Exception as e:
        logging.error(e)

def process_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url",
                        nargs="?",
                        type=str,
                        help="Single URL to scan with fingerprinting tools")
    parser.add_argument("-w", "--output-file",
                        type=str,
                        help="File to write probe outputs to. This argument is required if in record mode.",
                        default=None)
    parser.add_argument("-r", "--urls-file",
                        type=str,
                        help="File containing multiple URLs to run fingerprinting scans against")
    parser.add_argument("-t", "--testbed",
                        type=str,
                        help="Testbed to run in the 'testbeds' folder. Defaults to test_webapp",
                        default="fingerprint.testbed")
    parser.add_argument("-m", "--middleware-script",
                        type=str,
                        help="Middleware script to attach to mitmproxy instance",
                        default=None)
    parser.add_argument("--webapp-name",
                        type=str,
                        help="Web application to assume is being scanned",
                        default="guess")
    parser.add_argument("--worker-mode",
                        action="store_true",
                        help="Run in worker mode without setting up/tearing down shared resources")
    parser.add_argument("--network-name",
                        type=str,
                        default="fingerprint",
                        help="Name of the docker network to use")
    parser.add_argument("--proxy-name",
                        type=str,
                        default="mitmproxy",
                        help="Name of the mitmproxy container")
    args = vars(parser.parse_args())
    return args

if(__name__ == '__main__'):
    print("실행중")
    args = process_args()
    if(args == None):
        sys.exit(1)

    driver = None
    
    if not args['worker_mode']:
        try:
            driver = Driver(middleware_script=args["middleware_script"])

            if(args["urls_file"]):
                with open(args["urls_file"], "r") as f:
                    sites = [l.strip().split(',') for l in f]
            else:
                sites = [(args["webapp_name"], args["url"])]

            counter = 0
            for site in sites:
                if(counter == 2):
                    driver.middleware_container.restart(timeout=5)
                    time.sleep(3)
                    counter = 0

                print(site)
                driver.run_test(site[1], site[0], args["testbed"])
                counter+=1
        except Exception as e:
            logging.error(e)
        finally:
            if driver:
                driver.clean_up()
    else:
        try:
            if(args["urls_file"]):
                with open(args["urls_file"], "r") as f:
                    sites = [l.strip().split(',') for l in f]
            else:
                sites = [(args["webapp_name"], args["url"])]

            for site in sites:
                print(site)
                run_test_workermode(site[1], site[0], args["testbed"])
        except Exception as e:
            logging.error(e)
