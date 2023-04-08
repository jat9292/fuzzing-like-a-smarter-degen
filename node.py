import sys
import shutil
from typing import Generator
import subprocess
from time import sleep


class AnvilInstance:
    def __init__(self, provider: str, eth_address: str, eth_privkey: str):
        self.provider = provider
        self.eth_address = eth_address
        self.eth_privkey = eth_privkey


def fixture_anvil(port: int):
    """Fixture that runs anvil"""
    if not shutil.which("anvil"):
        raise Exception(
            "anvil was not found in PATH, you can install it by following: https://github.com/foundry-rs/foundry"
        )

    # Address #1 when anvil is run by default
    eth_address = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    eth_privkey = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    eth = int(1e6)
    proc = subprocess.Popen(
        f"""anvil --port {port} --chain-id 1 --accounts 3 --balance {eth} --steps-tracing""",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    sleep(3)
    return AnvilInstance(f"http://127.0.0.1:{port}", eth_address, eth_privkey), proc
