<p align="center">
	<img src="https://raw.githubusercontent.com/NHERI-SimCenter/pelicun/gh-pages/doc_src/common/figures/pelicun-Logo-white.png"
		alt="pelicun" align="middle" height="200"/>
</p>

<p align="center">
	<a href="https://doi.org/10.5281/zenodo.2558558", alt="DOI">
		<img src="https://zenodo.org/badge/DOI/10.5281/zenodo.2558558.svg" /></a>
</p>

<p align="center">
	<b>Probabilistic Estimation of Losses, Injuries, and Community resilience Under Natural hazard events</b>
</p>

![Tests](https://github.com/zsarnoczay/pelicun/actions/workflows/tests.yml/badge.svg)
[![codecov](https://codecov.io/github/zsarnoczay/pelicun/branch/develop/graph/badge.svg?token=W79M5FGOCG)](https://codecov.io/github/zsarnoczay/pelicun/tree/develop)

## What is it?

`pelicun` is a Python package that provides tools for assessment of damage and losses due to natural hazard events. It uses a stochastic damage and loss model that is an extension of the high-resolution PEER performance assessment methodology described in FEMA P58 (FEMA, 2012). While FEMA P58 aims to assess the seismic performance of a building, with `pelicun` we provide a more versatile, hazard-agnostic tool to assess the performance of several types of assets in the built environment.

Detailed documentation of the available methods and their use is available at http://nheri-simcenter.github.io/pelicun

## What can I use it for?

`pelicun` quantifies losses from an earthquake or hurricane scenario in the form of decision variables. This functionality is typically utilized for performance-based engineering and regional risk assessment. There are several steps of performance assessment that `pelicun` can help with:

- **Describe the joint distribution of asset response.** The response of a structure or other type of asset to an earthquake or hurricane wind is typically described by so-called engineering demand parameters (EDPs). `pelicun` provides methods that take a finite number of EDP vectors and find a multivariate distribution that describes the joint distribution of EDP data well. You can control the type of target distribution, apply truncation limits and censor part of the data to consider detection limits in your analysis. Alternatively, you can choose to use your EDP vectors as-is without resampling from a fitted distribution.

- **Define the damage and loss model of a building.** The component damage and loss data from the first two editions of FEMA P58 and the HAZUS earthquake and hurricane models for buildings are provided with pelicun. This makes it easy to define building components without having to collect and provide all the data manually. The stochastic damage and loss model is designed to facilitate modeling correlations between several parameters of the damage and loss model.

- **Estimate component damages.** Given a damage and loss model and the joint distribution of EDPs, `pelicun` provides methods to estimate the amount of damaged components and the number of cases with collapse.

- **Estimate consequences.** Using information about collapse and component damages, the following consequences can be estimated with the loss model: reconstruction cost and time, unsafe placarding (red tag), injuries and fatalities.

## Why should I use it?

1. It is free and it always will be.
2. It is open source. You can always see what is happening under the hood.
3. It is efficient. The loss assessment calculations in `pelicun` use `numpy`, `scipy`, and `pandas` libraries to efficiently propagate uncertainties and provide detailed results quickly.
4. You can trust it. Every function in `pelicun` is tested after every commit. See the Travis-CI and Coveralls badges at the top for more info.
5. You can extend it. If you have other methods that you consider better than the ones we already offer, we encourage you to fork the repo, and extend `pelicun` with your approach. You do not need to share your extended version with the community, but if you are interested in doing so, contact us and we are more than happy to merge your version with the official release.

## Installation

### For users

`pelicun` is available at the [Python Package Index (PyPI)](https://pypi.org/project/pelicun/). You can simply install it using `pip` as follows:

```shell
pip install pelicun
```

If you are interested in using an earlier version, you can install it with the following command: 

```shell
pip install pelicun==2.6.0
```

Note that 2.6.0 is the last minor version before the v3.0 release. Other earlier versions can be found [here](https://pypi.org/project/pelicun/#history).

### For contributors

Developers are expected to fork and clone this repository, and install their copy in development mode.
Using a virtual environment is highly recommended.

```shell
# Clone the repository:
git clone https://github.com/<user>/pelicun
cd pelicun

# Install pelicun:
# Note: don't forget to activate the corresponding environment.
python -m pip install -e .

# Install additional development setup dependencies
python -m pip install -r requirements_dev.txt

```

Contributions are managed with pull requests.
It is required that contributed code is [PEP 8](https://peps.python.org/pep-0008/) compliant, does not introduce linter warnings and includes sufficient unit tests so as to avoid reducing the current coverage level.

The following lines implement the aforementioned checks.
`flake8`, `pylint` and `pytest` can all be configured for use within an IDE.
```shell

cd <path-to>/pelicun
export PYTHONPATH=$PYTHONPATH:$(pwd)

# Linting with flake8:
flake8 pelicun

# Linting with pylint:
cd <path-to>/pelicun
pylint pelicun

# Running the tests:
python -m pytest pelicun/tests --cov=pelicun --cov-report html
# Open `htmlcov/index.html`in a browser to see coverage results.


```

Feel free to [open an issue](https://github.com/NHERI-SimCenter/pelicun/issues/new/choose) if you encounter problems setting up the provided development environment.


## Changelog

### Changes in v3.1

* Calculation settings are now assessment-specific. This allows you to use more than one assessments in an interactive calculation and each will have its own set of options, including log files.

* The uq module was decoupled from the others to enable standalone uq calculations that work without having an active assessment.

* A completely redesigned DL_calculation.py script that provides decoupled demand, damage, and loss assessment and more flexibility when setting up each of those when pelicun is used with a configuration file in a larger workflow.

* Two new examples that use the DL_calculation.py script and a json configuration file were added to the example folder.

* A new example that demonstrates a detailed interactive calculation in a Jupyter notebook was added to the following DesignSafe project: https://www.designsafe-ci.org/data/browser/public/designsafe.storage.published/PRJ-3411v5 This project will be extended with additional examples in the future.

* Unit conversion factors moved to an external file (settings/default_units) to make it easier to add new units to the list. This also allows redefining the internal units through a complete replacement of the factors. The internal units continue to follow the SI system.

* Substantial improvements in coding style using flake8 and pylint to monitor and help enforce PEP8.

* Several performance improvements made calculations more efficient, especially for large problems, such as regional assessments or tall buildings investigated using the FEMA P-58 methodology.

* Several bugfixes and a large number of minor changes that make the engine more robust and easier to use.

* Update recommended Python version to 3.10 and other dependencies to more recent versions. 

### Changes in v3.0

* The architecture was redesigned to better support interactive calculation and provide a low-level integration across all supported methods. This is the first release with the new architecture. Frequent updates are planned to provide additional examples, tests, and bugfixes in the next few months.  

* New `assessment` module introduced to replace `control` module:
  * Provides a high-level access to models and their methods
  * Integrates all types of assessments into a uniform approach
  * Most of the methods from the earlier `control` module were moved to the `model` module
  
* Decoupled demand, damage, and loss calculations:
  * Fragility functions and consequence functions are stored in separate files. Added new methods to the `db` module to prepare the corresponding data files and re-generated such data for FEMA P58 and Hazus earthquake assessments. Hazus hurricane data will be added in a future release.
  * Decoupling removed a large amount of redundant data from supporting databases and made the use of HDF and json files for such data unnecessary. All data are stored in easy-to-read csv files.
  * Assessment workflows can include all three steps (i.e., demand, damage, and loss) or only one or two steps. For example, damage estimates from one analysis can drive loss calculations in another one.
  
* Integrated damage and loss calculation across all methods and components:
  * This includes phenomena such as collapse, including various collapse modes, and irreparable damage.
  * Cascading damages and other interdependencies between various components can be introduced using a damage process file.
  * Losses can be driven by damages or demands. The former supports the conventional damage->consequence function approach, while the latter supports the use of vulnerability functions. These can be combined within the same analysis, if needed.
  * The same loss component can be driven by multiple types of damages. For example, replacement can be triggered by either collapse or irreparable damage.

* Introduced *Options* in the configuration file and in the `base` module:
  * These options handle settings that concern pelicun behavior;
  * general preferences that might affect multiple assessment models;
  * and settings that users would not want to change frequently.
  * Default settings are provided in a `default_config.json` file. These can be overridden by providing any of the prescribed keys with a user-defined value assigned to them in the configuration file for an analysis.

* Introduced consistent handling of units. Each csv table has a standard column to describe units of the data in it. If the standard column is missing, the table is assumed to use SI units.

* Introduced consistent handling of pandas MultiIndex objects in headers and indexes. When tabular data is stored in csv files, MultiIndex objects are converted to simple indexes by concatenating the strings at each level and separating them with a `-`. This facilitates post-processing csv files in pandas without impeding post-processing those files in non-Python environments.

* Updated the DL_calculation script to support the new architecture. Currently, only the config file input is used. Other arguments were kept in the script for backwards compatibility; future updates will remove some of those arguments and introduce new ones.

* The log files were redesigned to provide more legible and easy-to-read information about the assessment.

### Changes in v2.6

* Support EDPs with more than 3 characters and/or a variable in their name. For example, SA_1.0 or SA_T1
* Support fitting normal distribution to raw EDP data (lognormal was already available)
* Extract key settings to base.py to make them more accessible for users.
* Minor bugfixes mostly related to hurricane storm surge assessment

## License

`pelicun` is distributed under the BSD 3-Clause license, see LICENSE.

## Acknowledgment

This material is based upon work supported by the National Science Foundation under Grants No. 1612843 2131111. Any opinions, findings, and conclusions or recommendations expressed in this material are those of the authors and do not necessarily reflect the views of the National Science Foundation.

## Contact

Adam Zsarnóczay, NHERI SimCenter, Stanford University, adamzs@stanford.edu
