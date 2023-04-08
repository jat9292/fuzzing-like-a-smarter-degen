import os
import json
from typing import List, Dict


def get_functions(test_file_name) -> (List, Dict):
    functions = {}
    contract_set = set()

    with open(f"crytic-export/{test_file_name.split('/')[-1]}.json") as crytic_out:
        out_info = json.load(crytic_out)
        unit = list(out_info["compilation_units"].keys())[0]

        contracts = out_info["compilation_units"][unit]["contracts"][unit]
        contract_names = list(contracts.keys())

        for contract in contracts:
            contract_set.add(contract)
            functions[contract] = [
                data
                for data in contracts[contract]["abi"]
                if data["type"] == "function"
                and data["stateMutability"] != "view"
                and data["stateMutability"] != "pure"
            ]

            # If the internalType of an input starts with `contract` we should save it,
            # and look for it in the other abis, then deduce which functions are available to us

    return (contract_names, functions)


def get_abi_and_bytecode(test_file_name):
    abi = {}
    bytecode = {}
    contract_set = set()

    with open(f"crytic-export/{test_file_name.split('/')[-1]}.json") as crytic_out:
        out_info = json.load(crytic_out)
        unit = list(out_info["compilation_units"].keys())[0]

        contracts = out_info["compilation_units"][unit]["contracts"][unit]
        contract_names = list(contracts.keys())

        for contract in contracts:
            contract_set.add(contract)
            abi[contract] = contracts[contract]["abi"]
            bytecode[contract] = contracts[contract]["bin"]

    return (abi, bytecode)


def get_abi_by_name(contract_name,test_file_name):
    abi = {}

    with open(f"crytic-export/{test_file_name.split('/')[-1]}.json") as crytic_out:
        out_info = json.load(crytic_out)
        unit = list(out_info["compilation_units"].keys())[0]
        contracts = out_info["compilation_units"][unit]["contracts"][unit]

    return contracts[contract_name]["abi"]
