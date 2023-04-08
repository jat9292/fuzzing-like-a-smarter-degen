from slither import Slither
from slither.printers.guidance import echidna
from web3 import Web3
from hypothesis import strategies as st


def augment_strategies_with_constants(test_file_name, fuzz_candidates):
    # extract constants hardcoded in the smart contract
    slither = Slither(test_file_name)
    L_constants = dict()
    types_of_interest = ["int", "address", "string"]
    """
    We group uintN and intN in a unique int category
    SlithIR literals types <--> Solidity types 
    'uint256' : used for all uintN and bytesN
    'int256' : used for all intN
    'address' : for 'address' or 'address payable'
    'string' : used for string or bytes
    """
    for toi in types_of_interest:
        L_constants[toi] = set()

    for contract_name, dict_constants_per_contract in echidna._extract_constants(
        slither
    )[0].items():
        for function, list_constants_per_func in dict_constants_per_contract.items():
            for constant_value in list_constants_per_func:
                if constant_value.type == "address":
                    L_constants[constant_value.type].add(
                        Web3.to_checksum_address(hex(int(constant_value.value)))
                    )
                elif "int" in constant_value.type:  # uint or int
                    L_constants["int"].add(int(constant_value.value))
                elif constant_value.type == "string":
                    s = constant_value.value
                    L_constants[constant_value.type].add(s)

    def augment_simple_stg(stg):
        stg_augmented = stg
        if str(stg)[:8] == "integers":
            if hasattr(stg, "wrapped_strategy"):
                wstg = stg.wrapped_strategy
            else:
                wstg = stg
            L_ints_to_add = []
            for integer in L_constants["int"]:
                if integer >= wstg.start and integer <= wstg.end:
                    L_ints_to_add.append(integer)
            stg_augmented = st.one_of(st.sampled_from(L_ints_to_add), stg)
        if str(stg)[:4] == "text":
            stg_augmented = st.one_of(st.sampled_from(list(L_constants["string"])), stg)
        if str(stg) == "binary(min_size=20, max_size=20).map(to_checksum_address)":
            stg_augmented = st.one_of(
                st.sampled_from(list(L_constants["address"])), stg
            )
        return stg_augmented

    fuzz_candidates_augmented = []
    for fuzz_can in fuzz_candidates:
        if str(fuzz_can[1])[:6] == "tuples":
            elt_strategies = fuzz_can[1].wrapped_strategy.element_strategies
            List_stg_augmented = []
            for stg in elt_strategies:
                List_stg_augmented.append(augment_simple_stg(stg))
            fuzz_can[1].wrapped_strategy.element_strategies = tuple(List_stg_augmented)
            fuzz_candidates_augmented.append(fuzz_can)
        else:
            fuzz_can = fuzz_can[0], augment_simple_stg(fuzz_can[1])
            fuzz_candidates_augmented.append(fuzz_can)

    return fuzz_candidates_augmented
