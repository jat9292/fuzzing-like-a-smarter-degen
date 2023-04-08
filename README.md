## What is this?

This is an improved and heavily reworked fork of ["Fuzzing-Like-A-Degen"](https://www.youtube.com/watch?v=qdtQ9k3gCX8&t=282s&ab_channel=alpharush) in which many missing features were added : stateful testing, shrinking, coverage guidance, swarm testing, constants mining, faster local test node with anvil, etc. Although already usable as is, the current code is an early alpha version and many features are still missing for the moment (see TODO section).
Read the accompanying [Medium article](https://medium.com/p/1f73323c2b4d) for more information.

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

## TODO

Below is a non-exhaustive list of missing features which will be implemented soon™. Open source contributions are welcomed.

- [ ] Support paying ethers during transactions involving payable functions or payable fallback.
- [ ] Support sending transactions from several different accounts during the fuzzing campaign, instead of a single EOA.
- [ ] Support skipping blocks or fast forwarding in time.
- [ ] Improve the shrinking phase, especially when the `favor_long_sequence` parameter is set to `true`.
- [ ] The fuzzer does not support functions with a struct parameter : add support to fuzz struct parameters.
- [ ] Currently constants mining (i.e extracting hardcoded constants from code to use them as arguments during property-based testing) is only supported for `string`, `uintN`, `intN` and `address` parameters. `constants_minings` should also support other input types : `bytes`, `array`and `struct`.
- [ ] Some edge cases are still problematic : if a contract contains several functions with the same name or if several contracts share the same name.
- [ ] A nice feature and easy to implement, allowed by the Hypothesis library, is to let the user add one or several obectives which can be optimized simultanously during the fuzzing campaign. Currently only the coverage is (optionally) being optimized, but hyothesis is able to optimize the Pareto front of any list of targets, supplied by the user. So, in addition to a `setUp` and some `invariant` functions inside the tester contract, allow the user to define one or several `objective` functions which would return integer values to be optimized. This can be useful if for example an expert wants to guide the fuzzer towards states in which some variables would get close to some specific values.
- [ ] Perhaps change the default optimizer used by hypothesis for targeted property-based testing : the default optimizer is a simple hill-climbing which deals poorly with non-stationary objectives (hypothesis tests by default should not depend on an external global state), changing this could help with coverage-guided fuzzing. Especially if we want to use an energy score, like in AFLplus, which must be updated for each sampled test.
- [ ] Support functions taking no argument.
- [ ] Sometimes, the local test node is a bit unstable only during initialization (before the fuzzing campaign starts), and I have to rerun the fuzzer script. Investigate this issue.
