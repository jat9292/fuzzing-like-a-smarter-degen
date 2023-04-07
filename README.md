## What is this?

This is an improved and heavily reworked fork of ["Fuzzing-Like-A-Degen"](https://www.youtube.com/watch?v=qdtQ9k3gCX8&t=282s&ab_channel=alpharush) in which many missing features were added : stateful testing, shrinking, coverage guidance, swarm testing, constants mining, faster local test node with anvil, etc. Although already usable as is, the current code is an early alpha version and many features are still missing for the moment (see TODO section).

## Installation

Use an environement with either Python 3.8 or 3.9 or 3.10 . Then :

```shell
pip install -r requirements.txt
```

Install and activate solc 0.8.19 :

```
solc-select install 0.8.19
solc-select use 0.8.19
```

Install the [foundry framework](https://github.com/foundry-rs/foundry.git), in order to get anvil, its local Ethereum node, which is 40% faster than Ganache :

```
curl -L https://foundry.paradigm.xyz | bash
```

Then, in a new terminal (to update `PATH`), run the following command :

```
foundryup
```

## Usage

While working in the main directory (containing the `fuzzer.py` file), make sure to have a `config.yaml` file inside the same directory, this file contains all the parameters needed to configure the fuzzer, except the path to the tested smart contract. Look at the comments inside [the default `config.yaml`](config.yaml) to understand which options are available for each parameter, and the recommended default values.

Then run the fuzzer withthe following command :

```shell
python fuzzer.py [path_to_test_file]
```

Here, `path_to_test_file` is the path to the solidity file containing the smart contracts that you want to fuzz. The solidity file should contain, additionally to the contracts that you wish to test, one tester contract with at least one public `setUp()` fonction (which will be executed only once at the beginning of the fuzzing campaign, typically used to deploy the contracts to test) and one or several "invariant" functions representing the properties which should always hold if the tested contracts are correctly implemented. The invariant functions must have names starting with `invariant` which are public and returning boolean values : returning `false` if and only if the corresponding invariant is ever broken. See some example test files in the [tests/](tests/) directory.
