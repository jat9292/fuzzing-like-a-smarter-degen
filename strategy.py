from eth_abi.tools import get_abi_strategy
from abi import get_functions
from hypothesis import given, settings


def get_strategies(test_file_name):
    contract_names, functions = get_functions(test_file_name)
    for contract in contract_names:

        strats = []
        for func in functions[contract]:
            func_name = func["name"]
            args = func["inputs"]

            if len(args):
                if len(args) > 1:
                    arg_types = [arg["type"] for arg in args]
                    sig = f"({','.join(arg_types)})"  # (uint[3], uint)
                    strat = get_abi_strategy(sig)
                else:
                    strat = get_abi_strategy(args[0]["type"])
            else:
                continue

            func["strategy"] = strat

    return (contract_names, functions)
