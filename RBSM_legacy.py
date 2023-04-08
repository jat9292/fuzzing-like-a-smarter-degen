import sys
import os
import random
from datetime import timedelta
from web3 import Web3, HTTPProvider, Account
from node import fixture_anvil
from abi import get_abi_and_bytecode, get_abi_by_name
from strategy import get_strategies
import subprocess
import typer
import atexit
import yaml
from hypothesis import HealthCheck


class InvariantException(Exception):
    """Invariant function is not defined properly."""

    pass


def deploy_contract(w3, anvil, contract_names, test_file_name):
    """Deploy contract to the local anvil network."""
    abis, bytecodes = get_abi_and_bytecode(test_file_name)
    targets = []
    deployed_abis = []
    for contract in contract_names:
        abi = abis[contract]
        bytecode = bytecodes[contract]
        signed_txn = w3.eth.account.sign_transaction(
            dict(
                nonce=w3.eth.get_transaction_count(anvil.eth_address),
                maxFeePerGas=20000000000,
                maxPriorityFeePerGas=1,
                gas=15000000,
                to=b"",
                data="0x" + bytecode,
                chainId=1,
            ),
            anvil.eth_privkey,
        )
        tx_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction)
        address = w3.eth.get_transaction_receipt(tx_hash)["contractAddress"]
        target = w3.eth.contract(address, abi=abi)

        if "setUp" in target.functions:
            # record which contracts are deployed
            # remove this from functions to fuzz
            func = target.functions["setUp"]
            func().transact({"from": w3.eth.default_account.address})

            # We only fuzz contracts that have setUp functions
            for info in target.abi:
                if info["type"] == "function" and info["stateMutability"] == "view":
                    for ret in info["outputs"]:
                        internal_type = ret["internalType"]
                        if internal_type.startswith("contract"):
                            deployed = target.functions[info["name"]]().call(
                                {"from": w3.eth.default_account.address}
                            )
                            # TODO Deal with edge that contract names are the same
                            contract_name = internal_type.split(" ")[1]
                            deployed_abi = get_abi_by_name(
                                contract_name, test_file_name
                            )
                            targets.append(
                                w3.eth.contract(abi=deployed_abi, address=deployed)
                            )

            targets.append(target)

    return targets


def collect_functions(contract_names, functions, targets):
    invariants = []
    fuzz_candidates = []
    for contract in contract_names:
        for func in functions[contract]:
            is_invariant = False
            func_to_call = func["name"]

            if func_to_call.startswith("invariant"):
                try:
                    assert (
                        len(func["outputs"]) == 1
                        and func["outputs"][0]["internalType"] == "bool"
                    )
                except:
                    raise InvariantException(
                        f"{func_to_call} should have one boolean return value"
                    )

                is_invariant = True

            if func_to_call.startswith("setUp"):
                continue

            # TODO make sure duplicate function names don't cause strategy confusion
            for target in targets:
                if func_to_call in target.functions:
                    if is_invariant:
                        invariants.append(target.functions[func_to_call])
                    else:
                        fuzz_candidates.append(
                            (target.functions[func_to_call], func["strategy"])
                        )

    return invariants, fuzz_candidates


def fuzz(test_file_name: str, config_file: str = typer.Argument("config.yaml")):
    with open(config_file, "rb") as f:
        conf = yaml.safe_load(f.read())
    fuzz_runs = conf["fuzz_runs"]
    seq_len = conf["seq_len"]
    shrinking = conf["shrinking"]
    swarm_testing = conf["swarm_testing"]
    constants_mining = conf["constants_mining"]
    coverage_guidance = conf["coverage_guidance"]
    favor_long_sequence = conf["favor_long_sequence"]
    anvil_port = conf["anvil_port"]

    # Compile test contract
    try:
        subprocess.Popen(
            f"""crytic-compile --export-format standard {test_file_name}""",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except:
        raise Exception
        sys.exit(-1)

    # Anvil node
    anvil, proc = fixture_anvil(anvil_port)

    def exit_handler():
        proc.kill()
        proc.wait()

    atexit.register(
        exit_handler
    )  # closes the anvil node whenever the program stops (unexpectedly or not)

    # Provider
    w3 = Web3(HTTPProvider(anvil.provider, request_kwargs={"timeout": 30}))
    w3.eth.default_account = Account.from_key(anvil.eth_privkey)
    account = w3.eth.default_account.address
    try:
        assert w3.isConnected()
    except AttributeError:
        assert w3.is_connected()
    except:
        sys.exit(-1)

    contract_names, functions = get_strategies(test_file_name)
    targets = deploy_contract(w3, anvil, contract_names, test_file_name)
    os.remove(f"crytic-export/{test_file_name.split('/')[-1]}.json")
    snapshotID = 0
    invariants, fuzz_candidates = collect_functions(contract_names, functions, targets)

    from hypothesis import given, settings, note, Phase
    from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition

    stringStateFulFuzzer = f"""class StateFulFuzzer(RuleBasedStateMachine):

        def __init__(self):
            RuleBasedStateMachine.__init__(self)
            self.resetted = False

        @rule()
        @precondition(lambda self: not self.resetted)
        def reset_evm_state(self):
            global snapshotID
            if snapshotID==0:
                snapshotID = w3.provider.make_request('evm_snapshot', [])['result']
            else:
                w3.provider.make_request('evm_revert',[snapshotID])
                snapshotID = w3.provider.make_request('evm_snapshot', [])['result']
            self.resetted = True
    """

    for k in range(len(fuzz_candidates)):
        stringStateFulFuzzer += f"""
        @rule(arg=fuzz_candidates[{k}][1])
        @precondition(lambda self: self.resetted)
        def {fuzz_candidates[k][0].fn_name}(self,arg):
            func = fuzz_candidates[{k}][0]
            func(arg).transact({{'from': account}})
    """

    for k in range(len(invariants)):
        stringStateFulFuzzer += f"""
        @invariant()
        @precondition(lambda self: self.resetted)
        def {invariants[k].fn_name}(self):
            inv = invariants[{k}]
            result = inv().call({{'from': account}})
            assert result
    """

    exec(stringStateFulFuzzer, locals(), globals())

    if shrinking:
        phases_tuple = (
            Phase.explicit,
            Phase.reuse,
            Phase.generate,
            Phase.target,
            Phase.shrink,
        )
    else:
        phases_tuple = (Phase.explicit, Phase.reuse, Phase.generate, Phase.target)

    StateFulFuzzerTest = StateFulFuzzer.TestCase
    StateFulFuzzerTest.settings = settings(
        phases=phases_tuple,
        max_examples=fuzz_runs,
        stateful_step_count=seq_len,
        deadline=None,
    )
    try:
        StateFulFuzzerTest().runTest()
        print("No problem found, no invariant was broken")
    except AssertionError:
        print("Invariant broken")


if __name__ == "__main__":
    typer.run(fuzz)
