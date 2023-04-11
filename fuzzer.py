import sys
import os
import random
from datetime import timedelta
from web3 import Web3, HTTPProvider, Account
from web3._utils.method_formatters import BlockNotFound, TransactionNotFound
from node import fixture_anvil
from abi import get_abi_and_bytecode, get_abi_by_name
from utils import augment_strategies_with_constants
from hypothesis import given, settings, note, Phase, HealthCheck, target
from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, precondition
from hypothesis.core import Flaky
from hypothesis import strategies as st
from strategy import get_strategies
from collections import Counter
import subprocess
import typer
import atexit
import yaml
import string


class InvariantException(Exception):
    """Invariant function is not defined properly."""

    pass


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
                        deployed_abi = get_abi_by_name(contract_name, test_file_name)
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

    MAX_RETRY = (
        100  # to avoid rare connection error when deploying contracts to local node
    )
    for i in range(MAX_RETRY):
        try:
            targets = deploy_contract(w3, anvil, contract_names, test_file_name)
            break
        except (TransactionNotFound,ValueError):
            continue

    os.remove(f"crytic-export/{test_file_name.split('/')[-1]}.json")

    invariants, fuzz_candidates = collect_functions(contract_names, functions, targets)

    if constants_mining:
        fuzz_candidates = augment_strategies_with_constants(
            test_file_name, fuzz_candidates
        )

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

    operations = [
        st.tuples(st.just(fuzz_candidate[0]), fuzz_candidate[1])
        for fuzz_candidate in fuzz_candidates
    ]

    @st.composite
    def operations_list_strategy(draw):
        # Generate a random subset of operations
        if swarm_testing:
            min_size_sampled = len(operations) - draw(
                st.integers(0, len(operations) - 1)
            )
            unique_operations = st.sets(
                st.sampled_from(operations), min_size=min_size_sampled
            )
        else:
            unique_operations = st.just(operations)
        selected_operations = draw(unique_operations)
        if favor_long_sequence:
            min_seq_len_sampled = seq_len - draw(st.integers(0, seq_len - 1))
        else:
            min_seq_len_sampled = 1
        selected_ops = st.lists(
            st.one_of(selected_operations),
            min_size=min_seq_len_sampled,
            max_size=seq_len,
        )
        return draw(selected_ops)

    CounterCoverage = Counter()
    snapshotID = 0
    num_examples = 0
    current_max = 0
    dico_first_seen = dict()

    @settings(
        max_examples=fuzz_runs,
        phases=phases_tuple,
        deadline=None,
        suppress_health_check=list(HealthCheck),
    )
    @given(ops=operations_list_strategy())
    def composite_test(ops):
        seqCoverage = set()
        nonlocal snapshotID
        nonlocal num_examples
        nonlocal current_max

        def update_coverage_frequency(seqCov):
            nonlocal current_max
            if coverage_guidance:
                CounterCoverage.update(seqCov)
                covered_paths = [CounterCoverage[ID] for ID in seqCov]
                if len(covered_paths) > 0:  # to avoid rare flakiness bug in hypothesis
                    if 1 in covered_paths:  # new path discovered
                        selected_IDs = [
                            ID for ID, count in CounterCoverage.items() if count == 1
                        ]
                        for ID in selected_IDs:
                            dico_first_seen[ID] = num_examples
                        current_max = num_examples
                        target(num_examples)
                    else:
                        selected_values = [dico_first_seen[ID] for ID in seqCov]
                        max_value = max(selected_values)
                        if current_max == max_value:
                            target(num_examples)
                        else:
                            target(max_value)

        if snapshotID == 0:
            snapshotID = w3.provider.make_request("evm_snapshot", [])["result"]
        else:
            w3.provider.make_request("evm_revert", [snapshotID])
            snapshotID = w3.provider.make_request("evm_snapshot", [])["result"]
        num_examples += 1
        for op in ops:
            func = op[0]
            try:
                tx = func(op[1]).transact({"from": account})
                if coverage_guidance:
                    structLogs = w3.provider.make_request(
                        "debug_traceTransaction",
                        [tx.hex(), {"disableStorage": True, "disableStack": True}],
                    )["result"]["structLogs"]
                    structLogs_filtered = [
                        ele["pc"] for ele in structLogs if ele["depth"] == 1
                    ]
                    seqCoverage.update(set(structLogs_filtered))
                for inv in invariants:
                    result = inv().call({"from": account})
                    assert result
            except (
                BlockNotFound
            ):  # to avoid rare error when anvil fails to detect last block
                pass

        update_coverage_frequency(seqCoverage)

    try:
        composite_test()
        print("No problem found, no invariant was broken")
    except AssertionError or Flaky:
        print("Invariant broken")


if __name__ == "__main__":
    typer.run(fuzz)
