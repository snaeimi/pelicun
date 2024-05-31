"""
DL Calculation Example 3

"""

import tempfile
import os
import shutil
from pathlib import Path
import pytest
import pandas as pd
from pelicun.warnings import PelicunWarning
from pelicun.tools.DL_calculation import run_pelicun


# pylint: disable=missing-function-docstring
# pylint: disable=missing-yield-doc
# pylint: disable=missing-yield-type-doc
# pylint: disable=redefined-outer-name


@pytest.fixture
def obtain_temp_dir():

    # get the path of this file
    this_file = __file__

    initial_dir = os.getcwd()
    this_dir = str(Path(this_file).parent)

    temp_dir = tempfile.mkdtemp()

    yield this_dir, temp_dir

    # go back to the right directory, otherwise any tests that follow
    # could have issues.
    os.chdir(initial_dir)


def test_dl_calculation_3(obtain_temp_dir):

    this_dir, temp_dir = obtain_temp_dir

    # Copy all input files to a temporary directory.
    # All outputs will also go there.
    # This approach is more robust to changes in the output files over
    # time.
    os.chdir(this_dir)
    for file_name in ('170-AIM.json', 'response.csv'):
        shutil.copy(f'{this_dir}/{file_name}', f'{temp_dir}/{file_name}')
    os.chdir(temp_dir)

    # run
    with pytest.warns(PelicunWarning):
        return_int = run_pelicun(
            demand_file='response.csv',
            config_path='170-AIM.json',
            output_path=None,
            coupled_EDP=False,
            realizations='100',
            auto_script_path='PelicunDefault/Hazus_Earthquake_Story.py',
            detailed_results=False,
            regional=True,
            output_format=None,
            custom_model_dir=None,
            color_warnings=False,
        )

    assert return_int == 0

    #
    # Test files
    #

    # Ensure the number of files is as expected
    num_files = sum(1 for entry in Path(temp_dir).iterdir() if entry.is_file())
    assert num_files == 19

    # Verify their names
    files = {
        '170-AIM.json',
        '170-AIM_ap.json',
        'CMP_QNT.csv',
        'CMP_sample.json',
        'DEM_sample.json',
        'DL_summary.csv',
        'DL_summary.json',
        'DL_summary_stats.csv',
        'DL_summary_stats.json',
        'DMG_grp.json',
        'DMG_grp_stats.json',
        'DV_repair_agg.json',
        'DV_repair_agg_stats.json',
        'DV_repair_grp.json',
        'DV_repair_sample.json',
        'DV_repair_stats.json',
        'pelicun_log.txt',
        'pelicun_log_warnings.txt',
        'response.csv',
    }

    for file in files:
        assert Path(f'{temp_dir}/{file}').is_file()

    #
    # Check the values: TODO
    #
