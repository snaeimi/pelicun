# -*- coding: utf-8 -*-
#
# Copyright (c) 2018 Leland Stanford Junior University
# Copyright (c) 2018 The Regents of the University of California
#
# This file is part of pelicun.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice,
# this list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
#
# You should have received a copy of the BSD 3-Clause License along with
# pelicun. If not, see <http://www.opensource.org/licenses/>.
#
# Contributors:
# Adam Zsarnóczay

"""
This module has classes and methods that control the loss assessment.

.. rubric:: Contents

.. autosummary::

    Assessment
    FEMA_P58_Assessment
    HAZUS_Assessment

"""

from .base import *
from .uq import *
from .model import *
from .file_io import *


class Assessment(object):
    """
    A high-level class that collects features common to all supported loss
    assessment methods. This class will only rarely be called directly when
    using pelicun.
    """

    def __init__(self):

        # initialize the basic data containers
        # inputs
        self._AIM_in = None
        self._EDP_in = None
        self._POP_in = None
        self._FG_in = None

        # random variables and loss model
        self._RV_dict = None # dictionary to store random variables
        self._EDP_dict = None
        self._FG_dict = None

        # results
        self._TIME = None
        self._POP = None
        self._COL = None
        self._ID_dict = None
        self._DMG = None
        self._DV_dict = None
        self._SUMMARY = None

        self._assessment_type = 'generic'

        # initialize the log file
        set_log_file('pelicun_log.txt')
        
        log_msg(log_div)
        log_msg('Assessement Started')
        log_msg(log_div)

    @property
    def beta_tot(self):
        """
        Calculate the total additional uncertainty for post processing.

        The total additional uncertainty is the squared root of sum of squared
        uncertainties corresponding to ground motion and modeling.

        Returns
        -------
        beta_total: float
            The total uncertainty (logarithmic EDP standard deviation) to add
            to the EDP distribution. Returns None if no additional uncertainty
            is assigned.
        """

        AU = self._AIM_in['general']['added_uncertainty']

        beta_total = 0.
        if AU['beta_m'] is not None:
            beta_total += AU['beta_m'] ** 2.
        if AU['beta_gm'] is not None:
            beta_total += AU['beta_gm'] ** 2.

        # if no uncertainty is assigned, we return None
        if beta_total == 0:
            beta_total = None
        else:
            beta_total = np.sqrt(beta_total)

        return beta_total

    def read_inputs(self, path_DL_input, path_EDP_input, verbose=False):
        """
        Read and process the input files to describe the loss assessment task.

        Parameters
        ----------
        path_DL_input: string
            Location of the Damage and Loss input file. The file is expected to
            be a JSON with data stored in a standard format described in detail
            in the Input section of the documentation.
        path_EDP_input: string
            Location of the EDP input file. The file is expected to follow the
            output formatting of Dakota. The Input section of the documentation
            provides more information about the expected formatting.
        verbose: boolean, default: False
            If True, the method echoes the information read from the files.
            This can be useful to ensure that the information in the file is
            properly read by the method.
        """

        # read SimCenter inputs -----------------------------------------------
        log_msg(log_div)
        log_msg('Reading inputs...')

        # BIM file
        log_msg('\tBIM file...')
        self._AIM_in = read_SimCenter_DL_input(
            path_DL_input, assessment_type=self._assessment_type,
            verbose=verbose)

        data = self._AIM_in

        log_msg()
        log_msg('\t\tGlobal attributes / settings:')
        for att in ['stories', 'coupled_assessment', 'realizations']:
            log_msg('\t\t\t{}: {}'.format(att, data['general'][att]))

        log_msg()
        log_msg('\t\tPrescribed Decision Variables:')
        for dv, val in data['decision_variables'].items():
            if val:
                log_msg('\t\t\t{}'.format(dv))

        log_msg()
        log_msg("\t\tDamage and Loss Data Dir:")
        log_msg('\t\t\t{}'.format(data['data_sources']['path_CMP_data']))

        if data['decision_variables']['injuries']:
            log_msg()
            log_msg("\t\tPopulation Data Dir:")
            log_msg('\t\t\t{}'.format(data['data_sources']['path_POP_data']))

        log_msg()
        log_msg('\t\tUnits:')
        for dv, val in data['unit_names'].items():
            log_msg('\t\t\t{}: {} ({})'.format(dv, val, data['units'][dv]))

        log_msg()
        log_msg('\t\tResponse Model:')
        log_msg('\t\t\tDetection Limits:')
        for dl_name, dl in data['general']['detection_limits'].items():
            log_msg('\t\t\t\t{}: {}'.format(dl_name, dl))
        for att, val in data['general']['response'].items():
            log_msg()
            log_msg('\t\t\t{}: {}'.format(att, val))
        log_msg()
        log_msg('\t\t\tAdditional Uncertainty:')
        for att, val in data['general']['added_uncertainty'].items():
            log_msg('\t\t\t\t{}: {}'.format(att, val))

        log_msg()
        log_msg('\t\tPerformance Model:')
        log_msg('\t\t\t\tloc\tdir\tqnt\tdist\tcov\tcgw')
        for comp_id, comp_data in data['components'].items():
            log_msg('\t\t{} [{}]:'.format(comp_id, comp_data['unit']))
            if False: #TODO: control this with a verbose flag
                for i in range(len(comp_data['locations'])):
                    log_msg('\t\t\t\t{}\t{}\t{}\t{}\t{}\t{}'.format(*[comp_data[att][i] for att in ['locations', 'directions', 'quantities', 'distribution', 'cov', 'csg_weights']]))

        log_msg()
        log_msg('\t\tDamage Model:')
        if self._assessment_type == 'P58':
            log_msg('\t\t\tCollapse Limits:')
            for cl_name, cl in data['general']['collapse_limits'].items():
                log_msg('\t\t\t\t{}: {}'.format(cl_name, cl))
            log_msg()
            log_msg('\t\t\tIrrepairable Residual Drift:')
            for att, val in data['general']['irrepairable_res_drift'].items():
                log_msg('\t\t\t\t{}: {}'.format(att, val))
            log_msg()
            log_msg('\t\t\tCollapse Probability:')
            if data['general']['response']['coll_prob'] == 'estimated':
                log_msg('\t\t\t\tEstimated based on {}'.format(data['general']['response']['CP_est_basis']))
            else:
                log_msg('\t\t\t\tPrescribed: {}'.format(data['general']['response']['coll_prob']))

        log_msg()
        log_msg('\t\tLoss Model:')
        for att in ['replacement_cost', 'replacement_time', 'population']:
            if att in data['general'].keys():
                log_msg('\t\t\t{}: {}'.format(att, data['general'][att]))

        log_msg()
        log_msg('\t\tCollapse Modes:')
        for cmode, cmode_data in data['collapse_modes'].items():
            log_msg('\t\t\t{}'.format(cmode))
            for att, val in cmode_data.items():
                log_msg('\t\t\t  {}: {}'.format(att, val))

        log_msg()
        log_msg('\t\tDependencies:')
        for att, val in data['dependencies'].items():        
            log_msg('\t\t\t{}: {}'.format(att, val))

        # EDP file
        log_msg('\tEDP file...')
        if self._hazard == 'EQ':
            self._EDP_in = read_SimCenter_EDP_input(
                path_EDP_input,
                EDP_kinds=('PID', 'PFA', 'PGV', 'RID', 'PMD'),
                units=dict(PID=1.,
                           RID=1.,
                           PMD=1.,
                           PFA=self._AIM_in['units']['acceleration'],
                           PGV=self._AIM_in['units']['speed']),
                verbose=verbose)
        elif self._hazard == 'HU':
            self._EDP_in = read_SimCenter_EDP_input(
                path_EDP_input, EDP_kinds=('PWS',),
                units=dict(PWS=self._AIM_in['units']['speed']),
                verbose=verbose)

        data = self._EDP_in

        log_msg('\t\tEDP types:')
        for EDP_kind in data.keys():
            log_msg('\t\t\t{}'.format(EDP_kind))
            for EDP_data in data[EDP_kind]:
                if False: #TODO: control this with a verbose flag
                    log_msg('\t\t\t\t{} {}'.format(EDP_data['location'], EDP_data['direction']))

        log_msg()
        log_msg('\t\tnumber of samples: {}'.format(len(data[list(data.keys())[0]][0]['raw_data'])))        

    def define_random_variables(self):
        """
        Define the random variables used for loss assessment.

        """
        log_msg(log_div)
        log_msg('Defining random variables...')

    def define_loss_model(self):
        """
        Create the stochastic loss model based on the inputs provided earlier.

        """
        log_msg(log_div)
        log_msg('Creating the damage and loss model...')

    def calculate_damage(self):
        """
        Characterize the damage experienced in each random event realization.

        """
        log_msg(log_div)
        log_msg('Calculating damage...')
        self._ID_dict = {}

    def calculate_losses(self):
        """
        Characterize the consequences of damage in each random event realization.

        """
        log_msg(log_div)
        log_msg('Calculating losses...')
        self._DV_dict = {}

    def save_outputs(self, output_path, DM_file, DV_file, suffix=""):
        """
        Export the results.

        """
        def replace_FG_IDs_with_FG_names(df):
            FG_list = sorted(self._FG_dict.keys())
            new_col_names = dict(
                (fg_id, fg_name) for (fg_id, fg_name) in
                zip(np.arange(1, len(FG_list) + 1), FG_list))

            return df.rename(columns=new_col_names)

        log_msg(log_div)
        log_msg('Saving outputs...')

        log_msg('\tConverting EDP samples to input units...')
        EDPs = sorted(self._EDP_dict.keys())
        EDP_samples = self._EDP_dict[EDPs[0]]._RV.samples.copy()
        cols = EDP_samples.columns
        for col_i, col in enumerate(cols):
            if 'PFA' in col:
                scale_factor = self._AIM_in['units']['acceleration']
            elif ('PGV' in col) or ('PWS' in col):
                scale_factor = self._AIM_in['units']['speed']
            else:
                scale_factor = 1.0

            if scale_factor != 1.0:
                EDP_samples.iloc[:, col_i] = EDP_samples.iloc[:, col_i].div(scale_factor)

        log_msg('\tConverting damaged quantities to input units...')
        DMG_scaled = self._DMG.copy()
        cols = DMG_scaled.columns.get_level_values(0)        
        FG_list = sorted(self._FG_dict.keys())
        for col_i, col in enumerate(cols):
            FG_name = FG_list[col-1]
            scale_factor = self._FG_dict[FG_name]._unit
            if scale_factor != 1.0:
                DMG_scaled.iloc[:,col_i] = DMG_scaled.iloc[:,col_i].div(scale_factor)

        log_msg('\tReplacing headers with FG names...')        
        DMG_mod = replace_FG_IDs_with_FG_names(DMG_scaled)
        DV_mods, DV_names = [], []
        for key in self._DV_dict.keys():
            if key != 'injuries':
                DV_mods.append(replace_FG_IDs_with_FG_names(self._DV_dict[key]))
                DV_names.append('{}DV_{}'.format(suffix, key))
            else:
                for i in range(2 if self._assessment_type == 'P58' else 4):
                    DV_mods.append(replace_FG_IDs_with_FG_names(self._DV_dict[key][i]))
                    DV_names.append('{}DV_{}_{}'.format(suffix, key, i))

        #try:
        if True:
            log_msg('\tSaving files:')
            log_msg('\t\tSummary')
            write_SimCenter_DL_output(
                output_path, '{}DL_summary.csv'.format(suffix), 
                self._SUMMARY, index_name='#Num', collapse_columns=True)

            log_msg('\t\tSummary statistics')
            write_SimCenter_DL_output(
                output_path, '{}DL_summary_stats.csv'.format(suffix), 
                self._SUMMARY, index_name='attribute', collapse_columns=True,  
                stats_only=True)

            log_msg('\t\tEDP values')
            write_SimCenter_DL_output(
                output_path, '{}EDP.csv'.format(suffix), 
                EDP_samples, index_name='#Num', 
                collapse_columns=False)

            log_msg('\t\tEDP statistics')
            write_SimCenter_DL_output(
                output_path, '{}EDP_stats.csv'.format(suffix), 
                EDP_samples, index_name='#Num', 
                collapse_columns=False, stats_only=True)

            log_msg('\t\tDamaged quantities')
            write_SimCenter_DL_output(
                output_path, '{}DMG.csv'.format(suffix), 
                DMG_mod, index_name='#Num', collapse_columns=False)

            log_msg('\t\tDamage statistics')
            write_SimCenter_DL_output(
                output_path, '{}DMG_stats.csv'.format(suffix), 
                DMG_mod, index_name='#Num', 
                collapse_columns=False, stats_only=True)

            log_msg('\t\tDamaged quantities - aggregated')
            write_SimCenter_DL_output(
                output_path, '{}DMG_agg.csv'.format(suffix),
                DMG_mod.T.groupby(level=0).aggregate(np.sum).T,
                index_name='#Num', collapse_columns=False)

            for DV_mod, DV_name in zip(DV_mods, DV_names):
                log_msg('\t\tDecision variable {}'.format(DV_name))
                write_SimCenter_DL_output(
                    output_path, '{}{}.csv'.format(suffix, DV_name), 
                    DV_mod, index_name='#Num', collapse_columns=False)

                DV_mod_agg = DV_mod.T.groupby(level=0).aggregate(np.sum).T

                log_msg('\t\tDecision variable {} - aggregated'.format(DV_name))
                write_SimCenter_DL_output(
                    output_path, '{}{}_agg.csv'.format(suffix, DV_name),
                    DV_mod_agg, index_name='#Num', collapse_columns=False)

                log_msg('\t\tAggregated statistics for {}'.format(DV_name))
                write_SimCenter_DL_output(
                    output_path, '{}{}_agg_stats.csv'.format(suffix, DV_name), 
                    DV_mod_agg, index_name='#Num', collapse_columns=False, 
                    stats_only=True)

            #if True:
            # create the DM.json file
            if self._assessment_type.startswith('HAZUS'):
                log_msg('\t\tSimCenter DM file')
                write_SimCenter_DM_output(
                    output_path, suffix+DM_file,
                    DMG_mod)

            # create the DV.json file
            for DV_mod, DV_name in zip(DV_mods, DV_names):
                if self._assessment_type.startswith('HAZUS'):
                    log_msg('\t\tSimCenter DV file {}'.format(DV_name))
                    write_SimCenter_DV_output(
                        output_path, suffix+DV_file,
                        DV_mod, DV_name)

        #except:
        #    print("ERROR when trying to create DL output files.")

    def _create_RV_demands(self):

        # Unlike other random variables, the demand RV is based on raw data.

        # First, collect the raw values from the EDP dict...
        demand_data = []
        d_tags = []
        detection_limits = []
        collapse_limits = []
        GI = self._AIM_in['general']
        s_edp_keys = sorted(self._EDP_in.keys())

        for d_id in s_edp_keys:
            d_list = self._EDP_in[d_id]
            for i in range(len(d_list)):
                demand_data.append(d_list[i]['raw_data'])
                d_tags.append(str(d_id) +
                              '-LOC-' + str(d_list[i]['location']) +
                              '-DIR-' + str(d_list[i]['direction']))
                det_lim = GI['detection_limits'][d_id]
                if det_lim is None:
                    det_lim = np.inf
                if GI['response']['EDP_dist_basis'] == 'non-collapse results':
                    coll_lim = GI['collapse_limits'][d_id]
                    if coll_lim is None:
                        coll_lim = np.inf
                elif GI['response']['EDP_dist_basis'] == 'all results':
                    coll_lim = np.inf

                detection_limits.append([0., det_lim])
                collapse_limits.append([0., coll_lim])

        detection_limits = np.transpose(np.asarray(detection_limits))
        collapse_limits = np.transpose(np.asarray(collapse_limits))
        demand_data = np.transpose(np.asarray(demand_data))

        # If more than one sample is available...
        if demand_data.shape[0] > 1:

            # Second, we discard the collapsed EDPs if the fitted distribution shall
            # represent non-collapse EDPs.
            EDP_filter = np.all([np.all(demand_data > collapse_limits[0], axis=1),
                                 np.all(demand_data < collapse_limits[1], axis=1)],
                                axis=0)
            demand_data = demand_data[EDP_filter]

            log_msg('\t\t{} considered collapsed out of {} raw samples'.format(
                list(EDP_filter).count(False), len(EDP_filter)))

            # Third, we censor the EDPs that are beyond the detection limit.
            EDP_filter = np.all([np.all(demand_data > detection_limits[0], axis=1),
                                 np.all(demand_data < detection_limits[1], axis=1)],
                                axis=0)

            log_msg('\t\t{} are beyond the detection limits out of {} non-collapse samples'.format(
                list(EDP_filter).count(False), len(EDP_filter)))

            censored_count = len(EDP_filter) - sum(EDP_filter)
            demand_data = demand_data[EDP_filter]
            demand_data = np.transpose(demand_data)

            log_msg('\t\tNumber of EDP dimensions: {}'.format(len(d_tags)))

            # Fourth, we create the random variable
            demand_RV = RandomVariable(ID=200, dimension_tags=d_tags,
                                       raw_data=demand_data,
                                       detection_limits=detection_limits,
                                       censored_count=censored_count
                                       )

            # And finally, if requested, we fit a multivariate lognormal or a
            # truncated multivariate lognormal distribution to the censored raw
            # data.
            target_dist = GI['response']['EDP_distribution']

            if target_dist == 'lognormal':
                log_msg('\t\tFitting a lognormal distribution to samples...')
                demand_RV.fit_distribution('lognormal')
            elif target_dist == 'truncated lognormal':
                log_msg('\t\tFitting a truncated lognormal distribution to samples...')
                demand_RV.fit_distribution('lognormal', collapse_limits)

        # This is a special case when only a one sample is provided.
        else:
            # TODO: what to do when the sample is larger than the collapse or detection limit and when truncated distribution is prescribed

            # Since we only have one data point, the best we can do is assume
            # it is the median of the multivariate distribution. The dispersion
            # is assumed to be negligible.
            dim = len(demand_data[0])
            if dim > 1:
                sig = np.abs(demand_data[0])*1e-6
                rho = np.zeros((dim,dim))
                np.fill_diagonal(rho, 1.0)
                COV = np.outer(sig,sig) * rho
            else:
                COV = np.abs(demand_data[0][0])*(1e-6)**2.0

            demand_RV = RandomVariable(ID=200, dimension_tags=d_tags,
                                       distribution_kind='lognormal',
                                       theta=demand_data[0],
                                       COV=COV)

        # To consider additional uncertainty in EDPs, we need to redefine the
        # random variable. If the EDP distribution is set to 'empirical' then
        # adding uncertainty by increasing its variance is not possible.
        if ((self.beta_tot is not None) and
            (GI['response']['EDP_distribution'] != 'empirical')):
            log_msg('Considering additional sources of uncertainty...')
            # determine the covariance matrix with added uncertainty
            if demand_RV.COV.shape != ():
                sig_mod = np.sqrt(demand_RV.sig ** 2. + self.beta_tot ** 2.)
                COV_mod = np.outer(sig_mod, sig_mod) * demand_RV.corr
            else:
                COV_mod = np.sqrt(demand_RV.COV**2. + self.beta_tot**2.)

            # redefine the random variable
            demand_RV = RandomVariable(
                ID=200,
                dimension_tags=demand_RV.dimension_tags,
                distribution_kind=demand_RV.distribution_kind,
                theta=demand_RV.theta,
                COV=COV_mod)

        return demand_RV


class FEMA_P58_Assessment(Assessment):
    """
    An Assessment class that implements the loss assessment method in FEMA P58.
    """
    def __init__(self, inj_lvls = 2):
        super(FEMA_P58_Assessment, self).__init__()

        # constants for the FEMA-P58 methodology
        self._inj_lvls = inj_lvls
        self._hazard = 'EQ'
        self._assessment_type = 'P58'

        log_msg('type: FEMA P58 Assessment')
        log_msg('hazard: {}'.format(self._hazard))
        log_msg(log_div)

    def read_inputs(self, path_DL_input, path_EDP_input, verbose=False):
        """
        Read and process the input files to describe the loss assessment task.

        Parameters
        ----------
        path_DL_input: string
            Location of the Damage and Loss input file. The file is expected to
            be a JSON with data stored in a standard format described in detail
            in the Input section of the documentation.
        path_EDP_input: string
            Location of the EDP input file. The file is expected to follow the
            output formatting of Dakota. The Input section of the documentation
            provides more information about the expected formatting.
        verbose: boolean, default: False
            If True, the method echoes the information read from the files.
            This can be useful to ensure that the information in the file is
            properly read by the method.

        """

        super(FEMA_P58_Assessment, self).read_inputs(path_DL_input,
                                                     path_EDP_input, verbose)

        # assume that the asset is a building
        # TODO: If we want to apply FEMA-P58 to non-building assets, several parts of this methodology need to be extended.
        BIM = self._AIM_in

        # read component and population data ----------------------------------
        # components
        log_msg('\tDamage and Loss data files...')
        self._FG_in = read_component_DL_data(
            self._AIM_in['data_sources']['path_CMP_data'],
            BIM['components'],
            assessment_type=self._assessment_type, verbose=verbose)

        data = self._FG_in

        log_msg('\t\tAvailable Fragility Groups:')
        for key, val in data.items():
            log_msg('\t\t\t{} demand:{} PGs: {}'.format(key, val['demand_type'], len(val['locations']))) 

        # population (if needed)
        if self._AIM_in['decision_variables']['injuries']:
            log_msg('\tPopulation data files...')
            POP = read_population_distribution(
                self._AIM_in['data_sources']['path_POP_data'],
                BIM['general']['occupancy_type'],
                assessment_type=self._assessment_type,
                verbose=verbose)

            POP['peak'] = BIM['general']['population']
            self._POP_in = POP

    def define_random_variables(self):
        """
        Define the random variables used for loss assessment.

        Following the FEMA P58 methodology, the groups of parameters below are
        considered random. Simple correlation structures within each group can
        be specified through the DL input file. The random decision variables
        are only created and used later if those particular decision variables
        are requested in the input file.

        1. Demand (EDP) distribution

        Describe the uncertainty in the demands. Unlike other random variables,
        the EDPs are characterized by the EDP input data provided earlier. All
        EDPs are handled in one multivariate lognormal distribution. If more
        than one sample is provided, the distribution is fit to the EDP data.
        Otherwise, the provided data point is assumed to be the median value
        and the additional uncertainty prescribed describes the dispersion. See
        _create_RV_demands() for more details.

        2. Component quantities

        Describe the uncertainty in the quantity of components in each
        Performance Group. All Fragility Groups are handled in the same
        multivariate distribution. Consequently, correlation between various
        groups of component quantities can be specified. See
        _create_RV_quantities() for details.

        3. Fragility EDP limits

        Describe the uncertainty in the EDP limit that corresponds to
        exceedance of each Damage State. EDP limits are grouped by Fragility
        Groups. Consequently, correlation between fragility limits are
        currently limited within Fragility Groups. See
        _create_RV_fragilities() for details.

        4. Reconstruction cost and time

        Describe the uncertainty in the cost and duration of reconstruction of
        each component conditioned on the damage state of the component. All
        Fragility Groups are handled in the same multivariate distribution.
        Consequently, correlation between various groups of component
        reconstruction time and cost estimates can be specified. See
        _create_RV_repairs() for details.

        5. Damaged component proportions that trigger a red tag

        Describe the uncertainty in the amount of damaged components needed to
        trigger a red tag for the building. All Fragility Groups are handled in
        the same multivariate distribution. Consequently, correlation between
        various groups of component proportion limits can be specified. See
        _create_RV_red_tags() for details.

        6. Injuries

        Describe the uncertainty in the proportion of people in the affected
        area getting injuries exceeding a certain level of severity. FEMA P58
        uses two severity levels: injury and fatality. Both levels for all
        Fragility Groups are handled in the same multivariate distribution.
        Consequently, correlation between various groups of component injury
        expectations can be specified. See _create_RV_injuries() for details.
        """
        super(FEMA_P58_Assessment, self).define_random_variables()

        # create the random variables -----------------------------------------
        DEP = self._AIM_in['dependencies']

        self._RV_dict = {}

        # quantities 100
        log_msg('\tQuantities...')
        self._RV_dict.update({'QNT':
                              self._create_RV_quantities(DEP['quantities'])})

        log_msg('\t\tRV dimensions: {}'.format(len(self._RV_dict['QNT'].theta)))

        # fragilities 300
        log_msg('\tDamage State Limits...')
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id, c_name in enumerate(s_fg_keys):
            comp = self._FG_in[c_name]

            self._RV_dict.update({
                'FR-' + c_name:
                    self._create_RV_fragilities(c_id, comp,
                                                DEP['fragilities'])})

        log_msg('\t\tRV dimensions:')
        for key, val in self._RV_dict.items():
            if 'FR-' in key:
                log_msg('\t\t\t{}: {}'.format(key, len(val.theta)))

        # consequences 400
        DVs = self._AIM_in['decision_variables']

        if DVs['red_tag']:
            log_msg('\tRed Tag Thresholds...')
            self._RV_dict.update({'DV_RED':
                                  self._create_RV_red_tags(DEP['red_tags'])})

            log_msg('\t\tRV dimensions: {}'.format(len(self._RV_dict['DV_RED'].theta)))

        if DVs['rec_time'] or DVs['rec_cost']:
            log_msg('\tReconstruction Costs and Times...')
            self._RV_dict.update({'DV_REP':
                                  self._create_RV_repairs(
                                    DEP['rec_costs'],
                                    DEP['rec_times'],
                                    DEP['cost_and_time'])})

            log_msg('\t\tRV dimensions: {}'.format(len(self._RV_dict['DV_REP'].theta)))

        if DVs['injuries']:
            log_msg('\tInjury Probabilities...')
            self._RV_dict.update({'DV_INJ':
                                  self._create_RV_injuries(
                                    DEP['injuries'],
                                    DEP['injury_lvls'])})

            log_msg('\t\tRV dimensions: {}'.format(len(self._RV_dict['DV_INJ'].theta)))

        # demands 200
        log_msg('\tEDPs...')

        GR = self._AIM_in['general']['response']
        if GR['EDP_dist_basis'] == 'non-collapse results':
            discard_limits = self._AIM_in['general']['collapse_limits']
        else:
            discard_limits = None

        self._RV_dict.update({
            'EDP': self._create_RV_demands()})

        # sample the random variables -----------------------------------------
        log_msg()
        log_msg('Sampling the random variables...')

        realization_count = self._AIM_in['general']['realizations']
        is_coupled = self._AIM_in['general']['coupled_assessment']

        s_rv_keys = sorted(self._RV_dict.keys())
        for r_i in s_rv_keys:
            rv = self._RV_dict[r_i]
            if rv is not None:
                log_msg('\t{}...'.format(r_i))
                rv.sample_distribution(
                    sample_size=realization_count, preserve_order=is_coupled)

    def define_loss_model(self):
        """
        Create the stochastic loss model based on the inputs provided earlier.

        Following the FEMA P58 methodology, the components specified in the
        Damage and Loss input file are used to create Fragility Groups. Each
        Fragility Group corresponds to a component that might be present in
        the building at several locations. See _create_fragility_groups() for
        more details about the creation of Fragility Groups.

        """
        super(FEMA_P58_Assessment, self).define_loss_model()

        # fragility groups
        self._FG_dict = self._create_fragility_groups()

        # demands
        self._EDP_dict = dict(
            [(tag, RandomVariableSubset(self._RV_dict['EDP'],tags=tag))
             for tag in self._RV_dict['EDP']._dimension_tags])

    def calculate_damage(self):
        """
        Characterize the damage experienced in each random event realization.

        First, the time of the event (month, weekday/weekend, hour) is randomly
        generated for each realization. Given the event time, the number of
        people present at each floor of the building is calculated.

        Second, the realizations that led to collapse are filtered. See
        _calc_collapses() for more details on collapse estimation.

        Finally, the realizations that did not lead to building collapse are
        further investigated and the quantities of components in each damage
        state are estimated. See _calc_damage() for more details on damage
        estimation.

        """
        super(FEMA_P58_Assessment, self).calculate_damage()

        # event time - month, weekday, and hour realizations
        log_msg('\tSampling event time...')
        self._TIME = self._sample_event_time()

        # get the population conditioned on event time (if needed)
        if self._AIM_in['decision_variables']['injuries']:
            log_msg('\tSampling the population...')
            self._POP = self._get_population()

        # collapses
        log_msg('\tCalculating the number of collapses...')
        self._COL, collapsed_IDs = self._calc_collapses()
        self._ID_dict.update({'collapse':collapsed_IDs})
        log_msg('\t\t{} out of {} collapsed.'.format(
            len(collapsed_IDs), 
            self._AIM_in['general']['realizations']))

        # select the non-collapse cases for further analyses
        non_collapsed_IDs = self._TIME[
            ~self._TIME.index.isin(collapsed_IDs)].index.values.astype(int)
        self._ID_dict.update({'non-collapse': non_collapsed_IDs})

        # damage in non-collapses
        log_msg('\tCalculating the damage in the non-collapsed cases...')
        self._DMG = self._calc_damage()

    def calculate_losses(self):
        """
        Characterize the consequences of damage in each random event realization.

        For the sake of efficiency, only the decision variables requested in
        the input file are estimated. The following consequences are handled by
        this method:

        Reconstruction time and cost
        Estimate the irrepairable cases based on residual drift magnitude and
        the provided irrepairable drift limits. Realizations that led to
        irrepairable damage or collapse are assigned the replacement cost and
        time of the building when reconstruction cost and time is estimated.
        Repairable cases get a cost and time estimate for each Damage State in
        each Performance Group. For more information about estimating
        irrepairability see _calc_irrepairable() and reconstruction cost and
        time see _calc_repair_cost_and_time() methods.

        Injuries
        Collapse-induced injuries are based on the collapse modes and
        corresponding injury characterization. Injuries conditioned on no
        collapse are based on the affected area and the probability of
        injuries of various severity specified in the component data file. For
        more information about estimating injuries conditioned on collapse and
        no collapse, see _calc_collapse_injuries() and
        _calc_non_collapse_injuries, respectively.

        Red Tag
        The probability of getting an unsafe placard or red tag is a function
        of the amount of damage experienced in various Damage States for each
        Performance Group. The damage limits that trigger an unsafe placard are
        specified in the component data file. For more information on
        assigning red tags to realizations see the _calc_red_tag() method.

        """
        super(FEMA_P58_Assessment, self).calculate_losses()
        DVs = self._AIM_in['decision_variables']

        # red tag probability
        if DVs['red_tag']:
            log_msg('\tAssigning Red Tags...')
            DV_RED = self._calc_red_tag()

            self._DV_dict.update({'red_tag': DV_RED})

        # reconstruction cost and time
        if DVs['rec_cost'] or DVs['rec_time']:
            # irrepairable cases
            if 'irrepairable_res_drift' in self._AIM_in['general']:
                log_msg('\tIdentifying Irrepairable Cases...')
                irrepairable_IDs = self._calc_irrepairable()
                log_msg('\t\t{} out of {} non-collapsed cases are irrepairable.'.format(
                    len(irrepairable_IDs), len(self._ID_dict['non-collapse'])))
            else:
                irrepairable_IDs = np.array([])

            # collect the IDs of repairable realizations
            P_NC = self._TIME.loc[self._ID_dict['non-collapse']]
            repairable_IDs = P_NC[
                ~P_NC.index.isin(irrepairable_IDs)].index.values.astype(int)

            self._ID_dict.update({'repairable': repairable_IDs})
            self._ID_dict.update({'irrepairable': irrepairable_IDs})

            # reconstruction cost and time for repairable cases
            log_msg('\tCalculating Reconstruction cost and time...')
            DV_COST, DV_TIME = self._calc_repair_cost_and_time()

            if DVs['rec_cost']:
                self._DV_dict.update({'rec_cost': DV_COST})

            if DVs['rec_time']:
                self._DV_dict.update({'rec_time': DV_TIME})

        # injuries due to collapse
        if DVs['injuries']:
            log_msg('\tCalculating Injuries in Collapsed Cases...')
            COL_INJ = self._calc_collapse_injuries()

            # injuries in non-collapsed cases
            log_msg('\tCalculating Injuries in Non-Collapsed Cases...')
            DV_INJ_dict = self._calc_non_collapse_injuries()

            # store results
            if COL_INJ is not None:
                self._COL = pd.concat([self._COL, COL_INJ], axis=1)

            self._DV_dict.update({'injuries': DV_INJ_dict})

    def aggregate_results(self):
        """

        Returns
        -------

        """

        log_msg(log_div)
        log_msg('Aggregating results...')

        DVs = self._AIM_in['decision_variables']

        MI_raw = [
            ('event time', 'month'),
            ('event time', 'weekday?'),
            ('event time', 'hour'),
            ('inhabitants', ''),
            ('collapses', 'collapsed?'),
            ('collapses', 'mode'),
            ('red tagged?', ''),
            ('reconstruction', 'irrepairable?'),
            ('reconstruction', 'cost impractical?'),
            ('reconstruction', 'cost'),
            ('reconstruction', 'time impractical?'),
            ('reconstruction', 'time-sequential'),
            ('reconstruction', 'time-parallel'),
            ('injuries', 'sev. 1'),  # thanks, Laura S.!
            ('injuries', 'sev. 2'),
        ]

        ncID = self._ID_dict['non-collapse']
        colID = self._ID_dict['collapse']
        if DVs['rec_cost'] or DVs['rec_time']:
            repID = self._ID_dict['repairable']
            irID = self._ID_dict['irrepairable']

        MI = pd.MultiIndex.from_tuples(MI_raw)

        SUMMARY = pd.DataFrame(np.empty((
            self._AIM_in['general']['realizations'],
            len(MI))), columns=MI)
        SUMMARY[:] = np.NaN

        # event time
        for prop in ['month', 'weekday?', 'hour']:
            offset = 0
            if prop == 'month':
                offset = 1
            SUMMARY.loc[:, ('event time', prop)] = \
                self._TIME.loc[:, prop] + offset

        # collapses
        SUMMARY.loc[:, ('collapses', 'collapsed?')] = self._COL.iloc[:, 0]

        # red tag
        if DVs['red_tag']:
            SUMMARY.loc[ncID, ('red tagged?', '')] = \
                self._DV_dict['red_tag'].max(axis=1)

        # reconstruction cost
        if DVs['rec_cost']:
            SUMMARY.loc[ncID, ('reconstruction', 'cost')] = \
                self._DV_dict['rec_cost'].sum(axis=1)

            repl_cost = self._AIM_in['general']['replacement_cost']
            SUMMARY.loc[colID, ('reconstruction', 'cost')] = repl_cost

        if DVs['rec_cost'] or DVs['rec_time']:
            SUMMARY.loc[ncID, ('reconstruction', 'irrepairable?')] = 0
            SUMMARY.loc[irID, ('reconstruction', 'irrepairable?')] = 1

        if DVs['rec_cost']:
            SUMMARY.loc[irID, ('reconstruction', 'cost')] = repl_cost


            repair_impractical_IDs = SUMMARY.loc[
                SUMMARY.loc[:, ('reconstruction', 'cost')] > repl_cost].index
            SUMMARY.loc[repID, ('reconstruction', 'cost impractical?')] = 0
            SUMMARY.loc[repair_impractical_IDs,
                        ('reconstruction', 'cost impractical?')] = 1
            SUMMARY.loc[
                repair_impractical_IDs, ('reconstruction', 'cost')] = repl_cost

        # reconstruction time
        if DVs['rec_time']:
            SUMMARY.loc[ncID, ('reconstruction', 'time-sequential')] = \
                self._DV_dict['rec_time'].sum(axis=1)
            SUMMARY.loc[ncID, ('reconstruction', 'time-parallel')] = \
                self._DV_dict['rec_time'].max(axis=1)

            rep_time = self._AIM_in['general']['replacement_time']

            for t_label in ['time-sequential', 'time-parallel']:
                SUMMARY.loc[colID, ('reconstruction', t_label)] = rep_time
                SUMMARY.loc[irID, ('reconstruction', t_label)] = rep_time

            repair_impractical_IDs = \
                SUMMARY.loc[SUMMARY.loc[:, ('reconstruction',
                                            'time-parallel')] > rep_time].index
            SUMMARY.loc[repID, ('reconstruction', 'time impractical?')] = 0
            SUMMARY.loc[repair_impractical_IDs,('reconstruction',
                                                'time impractical?')] = 1
            SUMMARY.loc[repair_impractical_IDs, ('reconstruction',
                                                 'time-parallel')] = rep_time

        # injuries
        if DVs['injuries']:

            # inhabitants
            SUMMARY.loc[:, ('inhabitants', '')] = self._POP.sum(axis=1)

            if 'CM' in self._COL.columns:
                SUMMARY.loc[colID, ('collapses', 'mode')] = self._COL.loc[:, 'CM']

                SUMMARY.loc[colID, ('injuries', 'sev. 1')] = \
                    self._COL.loc[:, 'INJ-0']
                SUMMARY.loc[colID, ('injuries', 'sev. 2')] = \
                    self._COL.loc[:, 'INJ-1']

            SUMMARY.loc[ncID, ('injuries', 'sev. 1')] = \
                self._DV_dict['injuries'][0].sum(axis=1)
            SUMMARY.loc[ncID, ('injuries', 'sev. 2')] = \
                self._DV_dict['injuries'][1].sum(axis=1)

        self._SUMMARY = SUMMARY.dropna(axis=1,how='all')

    def save_outputs(self, *args, **kwargs):
        """

        Returns
        -------

        """
        super(FEMA_P58_Assessment, self).save_outputs(*args, **kwargs)

    def _create_correlation_matrix(self, rho_target, c_target=-1,
                                   include_CSG=False,
                                   include_DSG=False, include_DS=False):
        """

        Parameters
        ----------
        rho_target
        c_target
        include_CSG
        include_DSG
        include_DS

        Returns
        -------

        """

        # set the correlation structure
        rho_FG, rho_PG, rho_LOC, rho_DIR, rho_CSG, rho_DS = np.zeros(6)

        if rho_target in ['FG', 'PG', 'DIR', 'LOC', 'CSG', 'ATC', 'DS']:
            rho_DS = 1.0
        if rho_target in ['FG', 'PG', 'DIR', 'LOC', 'CSG']:
            rho_CSG = 1.0
        if rho_target in ['FG', 'PG', 'DIR']:
            rho_DIR = 1.0
        if rho_target in ['FG', 'PG', 'LOC']:
            rho_LOC = 1.0
        if rho_target in ['FG', 'PG']:
            rho_PG = 1.0
        if rho_target == 'FG':
            rho_FG = 1.0

        L_D_list = []
        dims = []
        DS_list = []
        ATC_rho = []
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id, c_name in enumerate(s_fg_keys):
            comp = self._FG_in[c_name]

            if ((c_target == -1) or (c_id == c_target)):
                c_L_D_list = []
                c_DS_list = []
                ATC_rho.append(comp['correlation'])

                if include_DSG:
                    DS_count = 0
                    s_dsg_keys = sorted(comp['DSG_set'].keys())
                    for dsg_i in s_dsg_keys:
                        DSG = comp['DSG_set'][dsg_i]
                        if include_DS:
                            DS_count += len(DSG['DS_set'])
                        else:
                            DS_count += 1
                else:
                    DS_count = 1

                #for loc in comp['locations']:
                #    if include_CSG:
                #        u_dirs = comp['directions']
                #    else:
                #        u_dirs = np.unique(comp['directions'])
                #    c_L_D_list.append([])
                #    for dir_ in u_dirs:
                #        c_DS_list.append(DS_count)
                #        for ds_i in range(DS_count):
                #            c_L_D_list[-1].append(dir_)

                for loc_u in np.unique(comp['locations']):
                    c_L_D_list.append([])
                    for loc, dir, csg_weights in zip(comp['locations'],
                                                     comp['directions'],
                                                     comp['csg_weights']):
                        if loc == loc_u:
                            if include_CSG:
                                csg_list = csg_weights
                            else:
                                csg_list = [1.0,]
                            for csg_ in csg_list:
                                c_DS_list.append(DS_count)
                                for ds_i in range(DS_count):
                                    c_L_D_list[-1].append(dir)

                c_dims = sum([len(loc) for loc in c_L_D_list])
                dims.append(c_dims)
                L_D_list.append(c_L_D_list)
                DS_list.append(c_DS_list)

        rho = np.ones((sum(dims), sum(dims))) * rho_FG

        f_pos_id = 0
        for c_id, (c_L_D_list, c_dims, c_DS_list) in enumerate(
            zip(L_D_list, dims, DS_list)):
            c_rho = np.ones((c_dims, c_dims)) * rho_PG

            # dependencies btw directions
            if rho_DIR != 0:
                c_pos_id = 0
                for loc_D_list in c_L_D_list:
                    l_dim = len(loc_D_list)
                    c_rho[c_pos_id:c_pos_id + l_dim,
                    c_pos_id:c_pos_id + l_dim] = rho_DIR
                    c_pos_id = c_pos_id + l_dim

            # dependencies btw locations
            if rho_LOC != 0:
                flat_dirs = []
                [[flat_dirs.append(dir_i) for dir_i in dirs] for dirs in
                 c_L_D_list]
                flat_dirs = np.array(flat_dirs)
                for u_dir in np.unique(flat_dirs):
                    dir_ids = np.where(flat_dirs == u_dir)[0]
                    for i in dir_ids:
                        for j in dir_ids:
                            c_rho[i, j] = rho_LOC

            if ((rho_CSG != 0) or (rho_target == 'ATC')):
                c_pos_id = 0
                if rho_target == 'ATC':
                    rho_to_use = float(ATC_rho[c_id])
                else:
                    rho_to_use = rho_CSG
                for loc_D_list in c_L_D_list:
                    flat_dirs = np.array(loc_D_list)
                    for u_dir in np.unique(flat_dirs):
                        dir_ids = np.where(flat_dirs == u_dir)[0]
                        for i in dir_ids:
                            for j in dir_ids:
                                c_rho[c_pos_id + i, c_pos_id + j] = rho_to_use
                    c_pos_id = c_pos_id + len(loc_D_list)

            if rho_DS != 0:
                c_pos_id = 0
                for l_dim in c_DS_list:
                    c_rho[c_pos_id:c_pos_id + l_dim,
                          c_pos_id:c_pos_id + l_dim] = rho_DS
                    c_pos_id = c_pos_id + l_dim

            rho[f_pos_id:f_pos_id + c_dims,
                f_pos_id:f_pos_id + c_dims] = c_rho
            f_pos_id = f_pos_id + c_dims

        np.fill_diagonal(rho, 1.0)

        return rho

    def _create_RV_quantities(self, rho_qnt):
        """

        Parameters
        ----------
        rho_qnt

        Returns
        -------

        """

        q_theta, q_sig, q_tag, q_dist = [np.array([]) for i in range(4)]

        # collect the parameters for each quantity dimension
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id in s_fg_keys:
            comp = self._FG_in[c_id]

            u_dirs = np.unique(comp['directions'])

            #dir_weights = comp['dir_weights']
            #theta_list = []
            #[[theta_list.append(qnt * dw)
            #  for dw in dir_weights] for qnt in comp['quantities']]

            theta_list = comp['quantities']
            q_theta = np.append(q_theta, theta_list)

            dist_list = comp['distribution_kind']
            q_dist = np.append(q_dist, dist_list)

            cov_list = comp['cov']
            for theta, dk, cov in list(zip(theta_list, dist_list, cov_list)):
                if dk == 'normal':
                    q_sig = np.append(q_sig, [cov*theta,])
                else:
                    q_sig = np.append(q_sig, [cov, ])

            q_tag = np.append(q_tag, [c_id + '-QNT-' + str(s_i) + '-' + str(d_i)
                                      for s_i, d_i
                                      in list(zip(comp['locations'],
                                                  comp['directions']))])

        dims = len(q_theta)
        rho = self._create_correlation_matrix(rho_qnt)
        q_COV = np.outer(q_sig, q_sig) * rho

        # add lower limits to ensure only positive quantities
        # zero is probably too low, and it might make sense to introduce upper
        # limits as well
        tr_lower = [0. for d in range(dims)]
        tr_upper = [None for d in range(dims)]
        # to avoid truncations affecting other dimensions when rho_QNT is large,
        # assign a post-truncation correlation structure
        corr_ref = 'post'

        # create a random variable for component quantities in performance groups
        if q_tag.size > 0:
            quantity_RV = RandomVariable(ID=100,
                                         dimension_tags=q_tag,
                                         distribution_kind=q_dist,
                                         theta=q_theta,
                                         COV=q_COV,
                                         truncation_limits=[tr_lower, tr_upper],
                                         corr_ref=corr_ref)
        else:
            quantity_RV = None

        return quantity_RV

    def _create_RV_fragilities(self, c_id, comp, rho_fr):
        """

        Parameters
        ----------
        c_id
        comp
        rho_fr

        Returns
        -------

        """

        # prepare the basic multivariate distribution data for one component subgroup considering all damage states
        d_theta, d_sig, d_tag, d_distr_kind = [np.array([]) for i in range(4)]

        s_dsg_keys = sorted(comp['DSG_set'].keys())
        for d_id in s_dsg_keys:
            DSG = comp['DSG_set'][d_id]
            d_theta = np.append(d_theta, DSG['theta'])
            d_sig = np.append(d_sig, DSG['sig'])
            d_tag = np.append(d_tag, comp['ID'] + '-' + str(d_id))
            d_distr_kind = np.append(d_distr_kind, DSG['distribution_kind'])
        dims = len(d_theta)

        # get the total number of random variables for this fragility group
        #rv_count = len(comp['locations']) * len(comp['directions']) * dims
        rv_count = sum([len(csg_w) for csg_w in comp['csg_weights']]) * dims

        # create the (empty) input arrays for the RV
        c_theta = np.zeros(rv_count)
        c_tag = np.empty(rv_count, dtype=object)
        c_sig = np.zeros(rv_count)
        c_distr_kind = np.empty(rv_count, dtype=object)

        pos_id = 0
        #for l_id in comp['locations']:
        #    # for each location-direction pair)
        #    for d_id, __ in enumerate(comp['directions']):
        #        # for each component-subgroup
        #        c_theta[pos_id:pos_id + dims] = d_theta
        #        c_sig[pos_id:pos_id + dims] = d_sig
        #        c_tag[pos_id:pos_id + dims] = [
        #            t + '-LOC-{}-CSG-{}'.format(l_id, d_id) for t in d_tag]
        #        c_distr_kind[pos_id:pos_id + dims] = d_distr_kind
        #        pos_id += dims

        for l_id, d_id, csg_list in zip(comp['locations'], comp['directions'],
                                        comp['csg_weights']):
            # for each location-direction pair)
            for csg_id, __ in enumerate(csg_list):
                # for each component-subgroup
                c_theta[pos_id:pos_id + dims] = d_theta
                c_sig[pos_id:pos_id + dims] = d_sig
                c_tag[pos_id:pos_id + dims] = [
                    t + '-LOC-{}-DIR-{}-CSG-{}'.format(l_id, d_id, csg_id)
                    for t in d_tag]
                c_distr_kind[pos_id:pos_id + dims] = d_distr_kind
                pos_id += dims

        # create the covariance matrix
        c_rho = self._create_correlation_matrix(rho_fr, c_target=c_id,
                                                include_DSG=True,
                                                include_CSG=True)
        c_COV = np.outer(c_sig, c_sig) * c_rho

        if c_tag.size > 0:
            fragility_RV = RandomVariable(ID=300 + c_id,
                                          dimension_tags=c_tag,
                                          distribution_kind=c_distr_kind,
                                          theta=c_theta,
                                          COV=c_COV)
        else:
            fragility_RV = None

        return fragility_RV

    def _create_RV_red_tags(self, rho_target):

        f_theta, f_sig, f_tag = [np.array([]) for i in range(3)]
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id, c_name in enumerate(s_fg_keys):
            comp = self._FG_in[c_name]

            d_theta, d_sig, d_tag = [np.array([]) for i in range(3)]

            s_dsg_keys = sorted(comp['DSG_set'].keys())
            for dsg_i in s_dsg_keys:
                DSG = comp['DSG_set'][dsg_i]
                s_ds_keys = sorted(DSG['DS_set'].keys())
                for ds_i in s_ds_keys:
                    DS = DSG['DS_set'][ds_i]
                    if 'red_tag' in DS.keys():
                        d_theta = np.append(d_theta, DS['red_tag']['theta'])
                        d_sig = np.append(d_sig, DS['red_tag']['cov'])
                    else:
                        # if there are no injuries assigned to this DS
                        d_theta = np.append(d_theta, 0)
                        d_sig = np.append(d_sig, 0.0001)
                    d_tag = np.append(d_tag,
                                      comp['ID'] + '-' + str(dsg_i) + '-' + str(
                                          ds_i))

            for loc, dir_ in zip(comp['locations'], comp['directions']):
                f_theta = np.append(f_theta, d_theta)
                f_sig = np.append(f_sig, d_sig)
                f_tag = np.append(f_tag,
                                  [t + '-LOC-{}-DIR-{}'.format(loc, dir_)
                                   for t in d_tag])

        rho = self._create_correlation_matrix(rho_target, c_target=-1,
                                              include_DSG=True,
                                              include_DS=True)

        # remove the unnecessary fields
        to_remove = np.where(f_theta == 0)[0]
        rho = np.delete(rho, to_remove, axis=0)
        rho = np.delete(rho, to_remove, axis=1)

        f_theta, f_sig, f_tag = [np.delete(f_vals, to_remove)
                                 for f_vals in [f_theta, f_sig, f_tag]]

        f_COV = np.outer(f_sig, f_sig) * rho

        tr_upper = 1. + (1. - f_theta) / f_theta

        if f_tag.size > 0:
            red_tag_RV = RandomVariable(ID=400,
                                        dimension_tags=f_tag,
                                        distribution_kind='normal',
                                        theta=np.ones(len(f_theta)),
                                        COV=f_COV,
                                        corr_ref='post',
                                        truncation_limits=[np.zeros(len(f_theta)),
                                                           tr_upper])
        else:
            red_tag_RV = None

        return red_tag_RV

    def _create_RV_repairs(self, rho_cost, rho_time, rho_cNt):

        # prepare the cost and time parts of the data separately
        ct_sig, ct_tag, ct_dkind = [np.array([]) for i in range(3)]
        for rho_target, name in zip([rho_cost, rho_time], ['cost', 'time']):

            f_sig, f_tag, f_dkind = [np.array([]) for i in range(3)]

            s_fg_keys = sorted(self._FG_in.keys())
            for c_id, c_name in enumerate(s_fg_keys):
                comp = self._FG_in[c_name]

                d_sig, d_tag, d_dkind = [np.array([]) for i in range(3)]

                s_dsg_keys = sorted(comp['DSG_set'].keys())
                for dsg_i in s_dsg_keys:
                    DSG = comp['DSG_set'][dsg_i]
                    s_ds_keys = sorted(DSG['DS_set'].keys())
                    for ds_i in s_ds_keys:
                        DS = DSG['DS_set'][ds_i]
                        d_sig = np.append(d_sig,
                                          DS['repair_{}'.format(name)]['cov'])
                        d_dkind = np.append(d_dkind,
                                            DS['repair_{}'.format(name)][
                                                'distribution_kind'])
                        d_tag = np.append(d_tag,
                                          comp['ID'] + '-' + str(
                                              dsg_i) + '-' + str(
                                              ds_i) + '-{}'.format(name))

                for loc, dir_ in zip(comp['locations'], comp['directions']):
                    f_sig = np.append(f_sig, d_sig)
                    f_dkind = np.append(f_dkind, d_dkind)
                    f_tag = np.append(f_tag,
                                      [t + '-LOC-{}-DIR-{}'.format(loc,
                                                                   dir_)
                                       for t in d_tag])

            ct_sig = np.append(ct_sig, f_sig)
            ct_tag = np.append(ct_tag, f_tag)
            ct_dkind = np.append(ct_dkind, f_dkind)

        rho_c = self._create_correlation_matrix(rho_cost, c_target=-1,
                                          include_DSG=True,
                                          include_DS=True)
        rho_t = self._create_correlation_matrix(rho_time, c_target=-1,
                                          include_DSG=True,
                                          include_DS=True)

        dims = len(ct_tag)
        ct_rho = np.zeros((dims, dims))

        dims = dims // 2
        if rho_cNt == False:
            ct_rho[:dims, :dims] = rho_c
            ct_rho[dims:, dims:] = rho_t
        else:
            # In the special case of mixing perfect correlation between
            # locations and directions, taking the envelope is not the
            # appropriate solution. Instead, the LOC & DIR -> PG approach is
            # used.
            if (((rho_cost == 'LOC') and (rho_time =='DIR')) or
                ((rho_cost == 'DIR') and (rho_time == 'LOC'))):
                rho_ct = self._create_correlation_matrix('PG', c_target=-1,
                                                         include_DSG=True,
                                                         include_DS=True)
            else:
                # We use the envelope in every other case.
                rho_ct = np.maximum(rho_c, rho_t)

            ct_rho[:dims, :dims] = rho_ct
            ct_rho[dims:, dims:] = rho_ct

            # apply the same blocks to the off-diagonal positions
            ct_rho[:dims, dims:] = rho_ct
            ct_rho[dims:, :dims] = rho_ct

        ct_COV = np.outer(ct_sig, ct_sig) * ct_rho

        if ct_tag.size > 0:
            repair_RV = RandomVariable(ID=401,
                                       dimension_tags=ct_tag,
                                       distribution_kind=ct_dkind,
                                       theta=np.ones(len(ct_sig)),
                                       COV=ct_COV,
                                       corr_ref='post',
                                       truncation_limits=[np.zeros(len(ct_sig)),
                                                          None])
        else:
            repair_RV = None

        return repair_RV

    def _create_RV_injuries(self, rho_target, rho_lvls):

        inj_lvls = self._inj_lvls

        # prepare the parts for different levels of injury separately
        full_theta, full_sig, full_tag = [np.array([]) for i in range(3)]
        for i_lvl in range(inj_lvls):

            f_theta, f_sig, f_tag = [np.array([]) for i in range(3)]
            s_fg_keys = sorted(self._FG_in.keys())
            for c_id, c_name in enumerate(s_fg_keys):
                comp = self._FG_in[c_name]

                d_theta, d_sig, d_tag = [np.array([]) for i in range(3)]

                s_dsg_keys = sorted(comp['DSG_set'].keys())
                for dsg_i in s_dsg_keys:
                    DSG = comp['DSG_set'][dsg_i]
                    s_ds_keys = sorted(DSG['DS_set'].keys())
                    for ds_i in s_ds_keys:
                        DS = DSG['DS_set'][ds_i]
                        if 'injuries' in DS.keys():
                            d_theta = np.append(
                                d_theta, DS['injuries']['theta'][i_lvl])
                            d_sig = np.append(
                                d_sig, DS['injuries']['cov'][i_lvl])
                        else:
                            # if there are no injuries assigned to this DS
                            d_theta = np.append(d_theta, 0)
                            d_sig = np.append(d_sig, 0.0001)
                        d_tag = np.append(d_tag,
                                          (comp['ID'] + '-' + str(dsg_i) + '-' +
                                           str(ds_i) + '-{}'.format(i_lvl)))

                for loc, dir_ in zip(comp['locations'], comp['directions']):
                    f_theta = np.append(f_theta, d_theta)
                    f_sig = np.append(f_sig, d_sig)
                    f_tag = np.append(f_tag,
                                      [t + '-LOC-{}-DIR-{}'.format(loc,
                                                                   dir_)
                                       for t in d_tag])

            full_theta = np.append(full_theta, f_theta)
            full_sig = np.append(full_sig, f_sig)
            full_tag = np.append(full_tag, f_tag)

        dims = len(full_tag)
        full_rho = np.zeros((dims, dims))
        dims = dims // inj_lvls

        # if correlation between different levels of severity is considered, add that to the matrix
        if rho_lvls:
            rho_i = self._create_correlation_matrix(rho_target, c_target=-1,
                                              include_DSG=True,
                                              include_DS=True)
            for i in range(inj_lvls):
                for j in range(inj_lvls):
                    full_rho[i * dims:(i + 1) * dims,
                    j * dims:(j + 1) * dims] = rho_i

        # and now add the values around the main diagonal
        for i in range(inj_lvls):
            rho_i = self._create_correlation_matrix(rho_target, c_target=-1,
                                              include_DSG=True,
                                              include_DS=True)
            full_rho[i * dims:(i + 1) * dims, i * dims:(i + 1) * dims] = rho_i

            # finally, remove the unnecessary lines
        to_remove = np.where(full_theta == 0)[0]
        full_rho = np.delete(full_rho, to_remove, axis=0)
        full_rho = np.delete(full_rho, to_remove, axis=1)

        full_theta, full_sig, full_tag = [np.delete(f_vals, to_remove)
                                          for f_vals in
                                          [full_theta, full_sig, full_tag]]

        full_COV = np.outer(full_sig, full_sig) * full_rho

        tr_upper = 1. + (1. - full_theta) / full_theta

        if full_tag.size > 0:
            injury_RV = RandomVariable(ID=402,
                                       dimension_tags=full_tag,
                                       distribution_kind='normal',
                                       theta=np.ones(len(full_sig)),
                                       COV=full_COV,
                                       corr_ref='post',
                                       truncation_limits=[np.zeros(len(full_sig)),
                                                          tr_upper])
        else:
            injury_RV = None

        return injury_RV

    def _create_fragility_groups(self):

        RVd = self._RV_dict
        DVs = self._AIM_in['decision_variables']

        # create a list for the fragility groups
        FG_dict = dict()

        s_fg_keys = sorted(self._FG_in.keys())
        for c_id in s_fg_keys:
            log_msg('\t{}...'.format(c_id))
            comp = self._FG_in[c_id]

            FG_ID = len(FG_dict.keys())+1

            # create a list for the performance groups
            performance_groups = []

            # one group for each of the stories prescribed by the user
            PG_locations = comp['locations']
            PG_directions = comp['directions']
            PG_csg_lists = comp['csg_weights']
            for loc, dir_, csg_list in zip(PG_locations, PG_directions,
                                           PG_csg_lists):
                PG_ID = 10000 * FG_ID + 10 * loc + dir_

                # get the quantity
                QNT = RandomVariableSubset(
                    RVd['QNT'],
                    tags=[c_id + '-QNT-' + str(loc) + '-' + str(dir_), ])

                # create the damage objects
                # consequences are calculated on a performance group level

                # create a list for the damage state groups and their tags
                DSG_list = []
                d_tags = []
                s_dsg_keys = sorted(comp['DSG_set'].keys())
                for dsg_i, DSG_ID in enumerate(s_dsg_keys):
                    DSG = comp['DSG_set'][DSG_ID]
                    d_tags.append(c_id + '-' + DSG_ID)

                    # create a list for the damage states
                    DS_set = []

                    s_ds_keys = sorted(DSG['DS_set'].keys())
                    for ds_i, DS_ID in enumerate(s_ds_keys):
                        DS = DSG['DS_set'][DS_ID]

                        # create the consequence functions
                        if DVs['rec_cost']:
                            data = DS['repair_cost']
                            f_median = prep_bounded_linear_median_DV(
                                **{k: data.get(k, None) for k in
                                   ('median_max', 'median_min',
                                    'quantity_lower', 'quantity_upper')})
                            cf_tag = c_id + '-' + DSG_ID + '-' + DS_ID + \
                                     '-cost' + \
                                     '-LOC-{}-DIR-{}'.format(loc, dir_)
                            CF_RV = RandomVariableSubset(RVd['DV_REP'],
                                                         tags=cf_tag)
                            CF_cost = ConsequenceFunction(DV_median=f_median,
                                                          DV_distribution=CF_RV)
                        else:
                            CF_cost = None

                        if DVs['rec_time']:
                            data = DS['repair_time']
                            f_median = prep_bounded_linear_median_DV(
                                **{k: data.get(k, None) for k in
                                   ('median_max', 'median_min', 'quantity_lower',
                                    'quantity_upper')})
                            cf_tag = c_id + '-' + DSG_ID + '-' + DS_ID + \
                                     '-time' + \
                                     '-LOC-{}-DIR-{}'.format(loc, dir_)
                            CF_RV = RandomVariableSubset(RVd['DV_REP'],
                                                         tags=cf_tag)
                            CF_time = ConsequenceFunction(DV_median=f_median,
                                                          DV_distribution=CF_RV)
                        else:
                            CF_time = None

                        if (DVs['red_tag']) and ('red_tag' in DS.keys()):
                            data = DS['red_tag']
                            if data['theta'] > 0:
                                f_median = prep_constant_median_DV(data['theta'])
                                cf_tag = c_id + '-' + DSG_ID + '-' + DS_ID + \
                                         '-LOC-{}-DIR-{}'.format(loc, dir_)
                                CF_RV = RandomVariableSubset(RVd['DV_RED'],
                                                             tags=cf_tag)
                                CF_red_tag = ConsequenceFunction(DV_median=f_median,
                                                                 DV_distribution=CF_RV)
                            else:
                                CF_red_tag = None
                        else:
                            CF_red_tag = None

                        if (DVs['injuries']) and ('injuries' in DS.keys()):
                            CF_inj_set = []
                            for inj_i, theta in enumerate(DS['injuries']['theta']):
                                if theta > 0.:
                                    f_median = prep_constant_median_DV(theta)
                                    cf_tag = c_id + '-' + DSG_ID + '-' + DS_ID + \
                                             '-{}-LOC-{}-DIR-{}'.format(inj_i, loc, dir_)
                                    CF_RV = RandomVariableSubset(RVd['DV_INJ'],
                                                                 tags=cf_tag)
                                    CF_inj_set.append(ConsequenceFunction(
                                        DV_median=f_median,
                                        DV_distribution=CF_RV))
                                else:
                                    CF_inj_set.append(None)
                        else:
                            CF_inj_set = [None,]

                        # add the DS to the list
                        if 'affected_area' in DS.keys():
                            AA = DS['affected_area']
                        else:
                            AA = 0.0
                        # TODO: make this smarter by making affected_area a property of DS
                        DS_set.append(DamageState(
                            ID=ds_i + 1,
                            description=DS['description'],
                            weight=DS['weight'],
                            affected_area=AA,
                            repair_cost_CF=CF_cost,
                            reconstruction_time_CF=CF_time,
                            red_tag_CF=CF_red_tag,
                            injuries_CF_set=CF_inj_set))

                    # add the DSG to the list
                    DSG_list.append(DamageStateGroup(
                        ID=dsg_i + 1,
                        DS_set=DS_set,
                        DS_set_kind=DSG['DS_set_kind']))

                # create the fragility functions
                FF_set = []
                #CSG_this = np.where(comp['directions']==dir_)[0]
                #PG_weights = np.asarray(comp['csg_weights'])[CSG_this]
                # normalize the weights
                #PG_weights /= sum(PG_weights)
                for csg_id, __ in enumerate(csg_list):
                    # assign the appropriate random variable to the fragility
                    # function
                    ff_tags = [t + '-LOC-{}-DIR-{}-CSG-{}'.format(loc, dir_,
                                                                  csg_id)
                               for t in d_tags]
                    EDP_limit = RandomVariableSubset(RVd['FR-' + c_id],
                                                     tags=ff_tags)
                    FF_set.append(FragilityFunction(EDP_limit))

                # create the performance group
                PG = PerformanceGroup(ID=PG_ID,
                                      location=loc,
                                      quantity=QNT,
                                      fragility_functions=FF_set,
                                      DSG_set=DSG_list,
                                      csg_weights=csg_list,
                                      direction=dir_
                                      )
                performance_groups.append(PG)

            # create the fragility group
            FG = FragilityGroup(ID=FG_ID,
                                #kind=comp['kind'],
                                demand_type=comp['demand_type'],
                                performance_groups=performance_groups,
                                directional=comp['directional'],
                                correlation=comp['correlation'],
                                demand_location_offset=comp['offset'],
                                incomplete=comp['incomplete'],
                                name=str(FG_ID) + ' - ' + comp['ID'],
                                description=comp['description']
                                )

            FG_dict.update({comp['ID']:FG})

        return FG_dict

    def _sample_event_time(self):

        sample_count = self._AIM_in['general']['realizations']

        # month - uniform distribution over [0,11]
        month = np.random.randint(0, 12, size=sample_count)

        # weekday - binomial with p=5/7
        weekday = np.random.binomial(1, 5. / 7., size=sample_count)

        # hour - uniform distribution over [0,23]
        hour = np.random.randint(0, 24, size=sample_count)

        data = pd.DataFrame(data={'month'   : month,
                                  'weekday?': weekday,
                                  'hour'    : hour},
                            dtype=int)

        return data

    def _get_population(self):
        """
        Use the population characteristics to generate random population samples.

        Returns
        -------

        """
        POPin = self._POP_in
        TIME = self._TIME

        POP = pd.DataFrame(
            np.ones((len(TIME.index), len(POPin['peak']))) * POPin['peak'],
            columns=['LOC' + str(loc + 1)
                     for loc in range(len(POPin['peak']))])

        weekdays = TIME[TIME['weekday?'] == 1].index
        weekends = TIME[~TIME.index.isin(weekdays)].index

        for col in POP.columns.values:
            POP.loc[weekdays, col] = (
                POP.loc[weekdays, col] *
                np.array(POPin['weekday']['daily'])[
                    TIME.loc[weekdays, 'hour'].values.astype(int)] *
                np.array(POPin['weekday']['monthly'])[
                    TIME.loc[weekdays, 'month'].values.astype(int)])

            POP.loc[weekends, col] = (
                POP.loc[weekends, col] *
                np.array(POPin['weekend']['daily'])[
                    TIME.loc[weekends, 'hour'].values.astype(int)] *
                np.array(POPin['weekend']['monthly'])[
                    TIME.loc[weekends, 'month'].values.astype(int)])

        return POP

    def _calc_collapses(self):

        # There are three options for determining which realizations ended in
        # collapse.
        GI = self._AIM_in['general']
        GR = GI['response']
        realizations = self._AIM_in['general']['realizations']

        # 1, The simplest case: prescribed collapse rate
        if GR['coll_prob'] != 'estimated':
            collapsed_IDs = np.random.choice(
                realizations,
                size=int(GR['coll_prob']*realizations),
                replace=False)

        # 2, Collapses estimated using EDP results
        elif GR['CP_est_basis'] == 'raw EDP':
            demand_data = []
            collapse_limits = []
            s_edp_keys = sorted(self._EDP_in.keys())
            for d_id in s_edp_keys:
                d_list = self._EDP_in[d_id]
                for i in range(len(d_list)):
                    demand_data.append(d_list[i]['raw_data'])

                    coll_lim = GI['collapse_limits'][d_id]
                    if coll_lim is None:
                        coll_lim = np.inf

                    collapse_limits.append([0., coll_lim])

            collapse_limits = np.transpose(np.asarray(collapse_limits))
            demand_data = np.transpose(np.asarray(demand_data))

            EDP_filter = np.all(
                [np.all(demand_data > collapse_limits[0], axis=1),
                 np.all(demand_data < collapse_limits[1], axis=1)],
                axis=0)
            coll_prob = 1.0 - sum(EDP_filter)/len(EDP_filter)
            collapsed_IDs = np.random.choice(
                realizations,
                size=int(coll_prob * realizations),
                replace=False)

        # 3, Collapses estimated using sampled EDP distribution
        elif GR['CP_est_basis'] == 'sampled EDP':
            collapsed_IDs = np.array([])
            s_edp_keys = sorted(self._EDP_dict.keys())
            for demand_ID in s_edp_keys:
                demand = self._EDP_dict[demand_ID]
                coll_df = pd.DataFrame()
                kind = demand_ID[:3]
                collapse_limit = self._AIM_in['general']['collapse_limits'][kind]
                if collapse_limit is not None:
                    EDP_samples = demand.samples
                    coll_df = EDP_samples[EDP_samples > collapse_limit]
                collapsed_IDs = np.concatenate(
                    (collapsed_IDs, coll_df.index.values))

        # get a list of IDs of the collapsed cases
        collapsed_IDs = np.unique(collapsed_IDs).astype(int)

        COL = pd.DataFrame(np.zeros(realizations), columns=['COL', ])
        COL.loc[collapsed_IDs, 'COL'] = 1

        return COL, collapsed_IDs

    def _calc_damage(self):

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)
        DMG = pd.DataFrame()

        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            log_msg('\t\t{}...'.format(fg_id))
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = []
            for DSG in PG_set[0]._DSG_set:
                for DS in DSG._DS_set:
                    DS_list.append(str(DSG._ID) + '-' + str(DS._ID))
            d_count = len(DS_list)

            MI = pd.MultiIndex.from_product([[FG._ID, ],
                                             [pg._ID for pg in PG_set],
                                             DS_list],
                                            names=['FG', 'PG', 'DS'])

            FG_damages = pd.DataFrame(np.zeros((NC_samples, len(MI))),
                                      columns=MI,
                                      index=ncID)

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID
                PG_qnt = PG._quantity.samples.loc[ncID]                

                # get the corresponding demands                 
                if not FG._directional:
                    demand_ID_list = []

                    for demand_ID in self._EDP_dict.keys():
                        if demand_ID[:3] == FG._demand_type:                            
                            demand_data = demand_ID.split('-')                            
                            if int(demand_data[2]) == PG._location + FG._demand_location_offset:
                                demand_ID_list.append(demand_ID)                            

                    EDP_samples = self._EDP_dict[demand_ID_list[0]].samples.loc[ncID]                    
                    if len(demand_ID_list)>1:
                        for demand_ID in demand_ID_list[1:]:
                            new_samples = self._EDP_dict[demand_ID].samples.loc[ncID]                            
                            EDP_samples = np.maximum(new_samples.values,
                                                     EDP_samples.values)

                else:
                    demand_ID = (FG._demand_type +
                             '-LOC-' + str(PG._location + FG._demand_location_offset) +
                             '-DIR-' + str(PG._direction))

                    if demand_ID in self._EDP_dict.keys():
                        EDP_samples = self._EDP_dict[demand_ID].samples.loc[ncID]
                    else:
                        # If the required demand is not available, then we are most
                        # likely analyzing a 3D structure using results from a 2D
                        # simulation. The best thing we can do in that particular
                        # case is to use the EDP from the 1 direction for all other
                        # directions.
                        demand_ID = (FG._demand_type +
                                     '-LOC-' + str(PG._location + FG._demand_location_offset) + '-DIR-1')
                        EDP_samples = self._EDP_dict[demand_ID].samples.loc[ncID]

                csg_w_list = PG._csg_weights

                for csg_i, csg_w in enumerate(csg_w_list):
                    DSG_df = PG._FF_set[csg_i].DSG_given_EDP(EDP_samples)

                    for DSG in PG._DSG_set:
                        in_this_DSG = DSG_df[DSG_df.values == DSG._ID].index
                        if DSG._DS_set_kind == 'single':
                            DS = DSG._DS_set[0]
                            DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                            FG_damages.loc[in_this_DSG,
                                           (FG._ID, PG_ID, DS_tag)] += csg_w
                        elif DSG._DS_set_kind == 'mutually exclusive':
                            DS_weights = [DS._weight for DS in DSG._DS_set]
                            DS_RV = RandomVariable(
                                ID=-1, dimension_tags=['me_DS', ],
                                distribution_kind='multinomial',
                                p_set=DS_weights)
                            DS_df = DS_RV.sample_distribution(
                                len(in_this_DSG)) + 1
                            for DS in DSG._DS_set:
                                DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                                in_this_DS = DS_df[DS_df.values == DS._ID].index
                                FG_damages.loc[in_this_DSG[in_this_DS],
                                               (FG._ID, PG_ID, DS_tag)] += csg_w
                        elif DSG._DS_set_kind == 'simultaneous':
                            DS_weights = [DS._weight for DS in DSG._DS_set]
                            DS_df = np.random.uniform(
                                size=(len(in_this_DSG), len(DS_weights)))
                            which_DS = DS_df < DS_weights
                            any_DS = np.any(which_DS, axis=1)
                            no_DS_ids = np.where(any_DS == False)[0]

                            while len(no_DS_ids) > 0:
                                DS_df_add = np.random.uniform(
                                    size=(len(no_DS_ids), len(DS_weights)))
                                which_DS_add = DS_df_add < DS_weights
                                which_DS[no_DS_ids] = which_DS_add

                                any_DS = np.any(which_DS_add, axis=1)
                                no_DS_ids = no_DS_ids[
                                    np.where(any_DS == False)[0]]

                            for ds_i, DS in enumerate(DSG._DS_set):
                                DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                                in_this_DS = which_DS[:, ds_i]
                                FG_damages.loc[in_this_DSG[in_this_DS], (
                                FG._ID, PG_ID, DS_tag)] += csg_w

                        else:
                            raise ValueError(
                                "Unknown damage state type: {}".format(
                                    DSG._DS_set_kind)
                            )

                FG_damages.iloc[:,pg_i * d_count:(pg_i + 1) * d_count] = \
                    FG_damages.mul(PG_qnt.iloc[:, 0], axis=0)

            DMG = pd.concat((DMG, FG_damages), axis=1)

        DMG.index = ncID

        # sort the columns to enable index slicing later
        DMG = DMG.sort_index(axis=1, ascending=True)

        return DMG

    def _calc_red_tag(self):
        idx = pd.IndexSlice

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)
        DV_RED = pd.DataFrame()

        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = self._DMG.loc[:, idx[FG._ID, PG_set[0]._ID, :]].columns
            DS_list = DS_list.levels[2][DS_list.codes[2]].values

            MI = pd.MultiIndex.from_product([[FG._ID, ],
                                             [pg._ID for pg in PG_set],
                                             DS_list],
                                            names=['FG', 'PG', 'DS'])

            FG_RED = pd.DataFrame(np.zeros((NC_samples, len(MI))),
                                  columns=MI,
                                  index=ncID)

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID
                PG_qnt = PG._quantity.samples.loc[ncID]

                PG_DMG = self._DMG.loc[:, idx[FG._ID, PG_ID, :]].div(
                    PG_qnt.iloc[:, 0],
                    axis=0)

                for d_i, d_tag in enumerate(DS_list):
                    dsg_i = int(d_tag[0]) - 1
                    ds_i = int(d_tag[-1]) - 1

                    DS = PG._DSG_set[dsg_i]._DS_set[ds_i]

                    if DS._red_tag_CF is not None:
                        RED_samples = DS.red_tag_dmg_limit(
                            sample_size=NC_samples)
                        RED_samples.index = ncID

                        is_red = PG_DMG.loc[:, (FG._ID, PG_ID, d_tag)].sub(
                            RED_samples, axis=0)

                        FG_RED.loc[:, (FG._ID, PG_ID, d_tag)] = (
                            is_red > 0.).astype(int)
                    else:
                        FG_RED.drop(labels=[(FG._ID, PG_ID, d_tag), ], axis=1,
                                    inplace=True)

            if FG_RED.size > 0:
                DV_RED = pd.concat((DV_RED, FG_RED), axis=1)

        # sort the columns to enable index slicing later
        DV_RED = DV_RED.sort_index(axis=1, ascending=True)

        return DV_RED

    def _calc_irrepairable(self):

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)

        # determine which realizations lead to irrepairable damage
        # get the max residual drifts
        RID_max = None
        PID_max = None
        s_edp_keys = sorted(self._EDP_dict.keys())
        for demand_ID in s_edp_keys:
            demand = self._EDP_dict[demand_ID]
            kind = demand_ID[:3]
            if kind == 'RID':
                r_max = demand.samples.loc[ncID].values
                if RID_max is None:
                    RID_max = r_max
                else:
                    RID_max = np.max((RID_max, r_max), axis=0)
            elif kind == 'PID':
                d_max = demand.samples.loc[ncID].values
                if PID_max is None:
                    PID_max = d_max
                else:
                    PID_max = np.max((PID_max, d_max), axis=0)

        if RID_max is None:
            if PID_max is not None:
                # we need to estimate residual drifts based on peak drifts
                RID_max = np.zeros(NC_samples)

                # based on Appendix C in FEMA P-58
                delta_y = self._AIM_in['general']['yield_drift']
                small = PID_max < delta_y
                medium = PID_max < 4 * delta_y
                large = PID_max >= 4 * delta_y

                RID_max[large] = PID_max[large] - 3 * delta_y
                RID_max[medium] = 0.3 * (PID_max[medium] - delta_y)
                RID_max[small] = 0.
            else:
                # If no drift data is available, then we cannot provide an estimate
                # of irrepairability. We assume that all non-collapse realizations
                # are repairable in this case.
                return np.array([])

        # get the probabilities of irrepairability
        irrep_frag = self._AIM_in['general']['irrepairable_res_drift']
        RV_irrep = RandomVariable(ID=-1, dimension_tags=['RED_irrep', ],
                                  distribution_kind='lognormal',
                                  theta=irrep_frag['Median'],
                                  COV=irrep_frag['Beta'] ** 2.
                                  )
        RED_irrep = RV_irrep.sample_distribution(NC_samples)['RED_irrep'].values

        # determine if the realizations are repairable
        irrepairable = RID_max > RED_irrep
        irrepairable_IDs = ncID[np.where(irrepairable)[0]]

        return irrepairable_IDs

    def _calc_repair_cost_and_time(self):

        idx = pd.IndexSlice
        DVs = self._AIM_in['decision_variables']

        DMG_by_FG_and_DS = self._DMG.groupby(level=[0, 2], axis=1).sum()

        repID = self._ID_dict['repairable']
        REP_samples = len(repID)
        DV_COST = pd.DataFrame(np.zeros((REP_samples, len(self._DMG.columns))),
                               columns=self._DMG.columns, index=repID)
        DV_TIME = deepcopy(DV_COST)

        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = self._DMG.loc[:, idx[FG._ID, PG_set[0]._ID, :]].columns
            DS_list = DS_list.levels[2][DS_list.codes[2]].values

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID

                for d_i, d_tag in enumerate(DS_list):
                    dsg_i = int(d_tag[0]) - 1
                    ds_i = int(d_tag[-1]) - 1

                    DS = PG._DSG_set[dsg_i]._DS_set[ds_i]

                    TOT_qnt = DMG_by_FG_and_DS.loc[repID, (FG._ID, d_tag)]
                    PG_qnt = self._DMG.loc[repID,
                                           (FG._ID, PG_ID, d_tag)]

                    # repair cost
                    if DVs['rec_cost']:
                        COST_samples = DS.unit_repair_cost(quantity=TOT_qnt)
                        DV_COST.loc[:,
                        (FG._ID, PG_ID, d_tag)] = COST_samples * PG_qnt

                    if DVs['rec_time']:
                        # repair time
                        TIME_samples = DS.unit_reconstruction_time(quantity=TOT_qnt)
                        DV_TIME.loc[:,
                        (FG._ID, PG_ID, d_tag)] = TIME_samples * PG_qnt

        # sort the columns to enable index slicing later
        if DVs['rec_cost']:
            DV_COST = DV_COST.sort_index(axis=1, ascending=True)
        else:
            DV_COST = None
        if DVs['rec_time']:
            DV_TIME = DV_TIME.sort_index(axis=1, ascending=True)
        else:
            DV_TIME = None

        return DV_COST, DV_TIME

    def _calc_collapse_injuries(self):

        inj_lvls = self._inj_lvls

        # calculate injuries for the collapsed cases
        # generate collapse modes
        colID = self._ID_dict['collapse']
        C_samples = len(colID)

        if C_samples > 0:

            inj_lvls = self._inj_lvls
            coll_modes = self._AIM_in['collapse_modes']
            P_keys = [cmk for cmk in coll_modes.keys()]
            P_modes = [coll_modes[k]['w'] for k in P_keys]

            # create the DataFrame that collects the decision variables
            inj_cols = ['CM',]
            for i in range(inj_lvls):
                inj_cols.append('INJ-{}'.format(i))
            COL_INJ = pd.DataFrame(np.zeros((C_samples, inj_lvls + 1)),
                                   columns=inj_cols, index=colID)

            CM_RV = RandomVariable(ID=-1, dimension_tags=['CM', ],
                                   distribution_kind='multinomial',
                                   p_set=P_modes)
            COL_INJ['CM'] = CM_RV.sample_distribution(C_samples).values

            # get the popoulation values corresponding to the collapsed cases
            P_sel = self._POP.loc[colID]

            # calculate the exposure of the popoulation
            for cm_i, cmk in enumerate(P_keys):
                mode_IDs = COL_INJ[COL_INJ['CM'] == cm_i].index
                CFAR = coll_modes[cmk]['affected_area']
                INJ = coll_modes[cmk]['injuries']
                for loc_i in range(len(CFAR)):
                    loc_label = 'LOC{}'.format(loc_i + 1)
                    if loc_label in P_sel.columns:
                        for inj_i in range(inj_lvls):
                            INJ_i = P_sel.loc[mode_IDs, loc_label] * CFAR[loc_i] * \
                                    INJ[inj_i]
                            COL_INJ.loc[mode_IDs, 'INJ-{}'.format(inj_i)] = (
                                COL_INJ.loc[mode_IDs, 'INJ-{}'.format(inj_i)].add(INJ_i, axis=0).values)

            return COL_INJ

        else:
            return None

    def _calc_non_collapse_injuries(self):

        idx = pd.IndexSlice

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)
        DV_INJ_dict = dict([(i, pd.DataFrame(np.zeros((NC_samples,
                                                       len(self._DMG.columns))),
                                             columns=self._DMG.columns,
                                             index=ncID))
                            for i in range(self._inj_lvls)])
        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = self._DMG.loc[:, idx[FG._ID, PG_set[0]._ID, :]].columns
            DS_list = DS_list.levels[2][DS_list.codes[2]].values

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID

                for d_i, d_tag in enumerate(DS_list):
                    dsg_i = int(d_tag[0]) - 1
                    ds_i = int(d_tag[-1]) - 1

                    DS = PG._DSG_set[dsg_i]._DS_set[ds_i]

                    if DS._affected_area > 0.:
                        P_affected = (self._POP.loc[ncID]
                                      * DS._affected_area /
                                      self._AIM_in['general']['plan_area'])

                        QNT = self._DMG.loc[:, (FG._ID, PG_ID, d_tag)]

                        # estimate injuries
                        for i in range(self._inj_lvls):
                            INJ_samples = DS.unit_injuries(severity_level=i,
                                                           sample_size=NC_samples)
                            if INJ_samples is not None:
                                INJ_samples.index = ncID
                                P_aff_i = P_affected.loc[:,
                                          'LOC{}'.format(PG._location)]
                                INJ_i = INJ_samples * P_aff_i * QNT
                                DV_INJ_dict[i].loc[:,
                                (FG._ID, PG_ID, d_tag)] = INJ_i

                                # remove the useless columns from DV_INJ
        for i in range(self._inj_lvls):
            DV_INJ = DV_INJ_dict[i]
            DV_INJ_dict[i] = DV_INJ.loc[:, (DV_INJ != 0.0).any(axis=0)]

        # sort the columns to enable index slicing later
        for i in range(self._inj_lvls):
            DV_INJ_dict[i] = DV_INJ_dict[i].sort_index(axis=1, ascending=True)

        return DV_INJ_dict


class HAZUS_Assessment(Assessment):
    """
    An Assessment class that implements the damage and loss assessment method
    following the HAZUS Technical Manual and the HAZUS software.

    Parameters
    ----------
    hazard:  {'EQ', 'HU'}
        Identifies the type of hazard. EQ corresponds to earthquake, HU
        corresponds to hurricane.
        default: 'EQ'.
    inj_lvls: int
        Defines the discretization used to describe the severity of injuries.
        The HAZUS earthquake methodology uses 4 levels.
        default: 4
    """
    def __init__(self, hazard='EQ', inj_lvls = 4):
        super(HAZUS_Assessment, self).__init__()

        self._inj_lvls = inj_lvls
        self._hazard = hazard
        self._assessment_type = 'HAZUS_{}'.format(hazard)

    def read_inputs(self, path_DL_input, path_EDP_input, verbose=False):
        """
        Read and process the input files to describe the loss assessment task.

        Parameters
        ----------
        path_DL_input: string
            Location of the Damage and Loss input file. The file is expected to
            be a JSON with data stored in a standard format described in detail
            in the Input section of the documentation.
        path_EDP_input: string
            Location of the EDP input file. The file is expected to follow the
            output formatting of Dakota. The Input section of the documentation
            provides more information about the expected formatting.
        verbose: boolean, default: False
            If True, the method echoes the information read from the files.
            This can be useful to ensure that the information in the file is
            properly read by the method.

        """

        super(HAZUS_Assessment, self).read_inputs(path_DL_input,
                                                  path_EDP_input, verbose)

        # assume that the asset is a building
        # TODO: If we want to apply HAZUS to non-building assets, several parts of this methodology need to be extended.
        BIM = self._AIM_in

        # read component and population data ----------------------------------
        # components
        self._FG_in = read_component_DL_data(
            self._AIM_in['data_sources']['path_CMP_data'], BIM['components'],
            assessment_type=self._assessment_type, verbose=verbose)

        # population (if needed)
        if self._AIM_in['decision_variables']['injuries']:
            POP = read_population_distribution(
                self._AIM_in['data_sources']['path_POP_data'],
                BIM['general']['occupancy_type'],
                assessment_type=self._assessment_type,
                verbose=verbose)

            POP['peak'] = BIM['general']['population']
            self._POP_in = POP

    def define_random_variables(self):
        """
        Define the random variables used for loss assessment.

        Following the HAZUS methodology, only the groups of parameters below
        are considered random. Correlations within groups are not considered
        because each Fragility Group has only one Performance Group with a
        in this implementation.

        1. Demand (EDP) distribution

        Describe the uncertainty in the demands. Unlike other random variables,
        the EDPs are characterized by the EDP input data provided earlier. All
        EDPs are handled in one multivariate lognormal distribution. If more
        than one sample is provided, the distribution is fit to the EDP data.
        Otherwise, the provided data point is assumed to be the median value
        and the additional uncertainty prescribed describes the dispersion. See
        _create_RV_demands() for more details.

        2. Fragility EDP limits

        Describe the uncertainty in the EDP limit that corresponds to
        exceedance of each Damage State. EDP limits are grouped by Fragility
        Groups. See _create_RV_fragilities() for details.

        """
        super(HAZUS_Assessment, self).define_random_variables()

        DEP = self._AIM_in['dependencies']

        # create the random variables -----------------------------------------
        self._RV_dict = {}

        # quantities 100
        self._RV_dict.update({
            'QNT': self._create_RV_quantities(DEP['quantities'])})

        # fragilities 300
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id, c_name in enumerate(s_fg_keys):
            comp = self._FG_in[c_name]

            self._RV_dict.update({
                'FR-' + c_name:
                    self._create_RV_fragilities(c_id, comp,DEP['fragilities'])})

        # demands 200
        self._RV_dict.update({'EDP': self._create_RV_demands()})

        # sample the random variables -----------------------------------------
        realization_count = self._AIM_in['general']['realizations']
        is_coupled = self._AIM_in['general']

        s_rv_keys = sorted(self._RV_dict.keys())
        for r_i in s_rv_keys:
            rv = self._RV_dict[r_i]
            if rv is not None:
                rv.sample_distribution(
                    sample_size=realization_count, preserve_order=is_coupled)

    def define_loss_model(self):
        """
        Create the stochastic loss model based on the inputs provided earlier.

        Following the HAZUS methodology, the component assemblies specified in
        the Damage and Loss input file are used to create Fragility Groups.
        Each Fragility Group corresponds to one assembly that represents every
        component of the given type in the structure. See
        _create_fragility_groups() for more details about the creation of
        Fragility Groups.

        """
        super(HAZUS_Assessment, self).define_loss_model()

        # fragility groups
        self._FG_dict = self._create_fragility_groups()

        # demands
        self._EDP_dict = dict(
            [(tag, RandomVariableSubset(self._RV_dict['EDP'], tags=tag))
             for tag in self._RV_dict['EDP']._dimension_tags])

    def calculate_damage(self):
        """
        Characterize the damage experienced in each random event realization.

        First, the time of the event (month, weekday/weekend, hour) is randomly
        generated for each realization. Given the event time, the number of
        people present at each floor of the building is calculated.

        Next, the quantities of components in each damage state are estimated.
        See _calc_damage() for more details on damage estimation.

        """
        super(HAZUS_Assessment, self).calculate_damage()

        # event time - month, weekday, and hour realizations
        self._TIME = self._sample_event_time()

        # if we are interested in injuries...
        if self._AIM_in['decision_variables']['injuries']:
            # get the population conditioned on event time
            self._POP = self._get_population()

        # collapses are handled as the ultimate DS in HAZUS
        self._ID_dict.update({'collapse': []})

        # select the non-collapse cases for further analyses
        non_collapsed_IDs = self._TIME.index.values.astype(int)
        self._ID_dict.update({'non-collapse': non_collapsed_IDs})

        # damage in non-collapses
        self._DMG = self._calc_damage()

    def calculate_losses(self):
        """
        Characterize the consequences of damage in each random event realization.

        For the sake of efficiency, only the decision variables requested in
        the input file are estimated. The following consequences are handled by
        this method for a HAZUS assessment:

        Reconstruction time and cost
        Get a cost and time estimate for each Damage State in each Performance
        Group. For more information about estimating reconstruction cost and
        time see _calc_repair_cost_and_time() methods.

        Injuries
        The number of injuries are based on the probability of injuries of
        various severity specified in the component data file. For more
        information about estimating injuries _calc_non_collapse_injuries.

        """
        super(HAZUS_Assessment, self).calculate_losses()
        DVs = self._AIM_in['decision_variables']

        # reconstruction cost and time
        if DVs['rec_cost'] or DVs['rec_time']:
            # all damages are considered repairable in HAZUS
            repairable_IDs = self._ID_dict['non-collapse']
            self._ID_dict.update({'repairable': repairable_IDs})
            self._ID_dict.update({'irrepairable': []})

            # reconstruction cost and time for repairable cases
            DV_COST, DV_TIME = self._calc_repair_cost_and_time()

            if DVs['rec_cost']:
                self._DV_dict.update({'rec_cost': DV_COST})

            if DVs['rec_time']:
                self._DV_dict.update({'rec_time': DV_TIME})

        # injuries due to collapse
        if DVs['injuries']:
            # there are no separate collapse cases in HAZUS

            # injuries in non-collapsed cases
            DV_INJ_dict = self._calc_non_collapse_injuries()

            # store result
            self._DV_dict.update({'injuries': DV_INJ_dict})

    def aggregate_results(self):
        """

        Returns
        -------

        """

        DVs = self._AIM_in['decision_variables']

        MI_raw = [
            ('event time', 'month'),
            ('event time', 'weekday?'),
            ('event time', 'hour'),
            ('reconstruction', 'cost'),
        ]

        if DVs['rec_time']:
            MI_raw += [
                ('reconstruction', 'time'),
            ]

        if DVs['injuries']:
            MI_raw += [
                ('inhabitants', ''),
                ('injuries', 'sev. 1'),
                ('injuries', 'sev. 2'),
                ('injuries', 'sev. 3'),
                ('injuries', 'sev. 4'),
            ]

        ncID = self._ID_dict['non-collapse']
        colID = self._ID_dict['collapse']
        if DVs['rec_cost'] or DVs['rec_time']:
            repID = self._ID_dict['repairable']
            irID = self._ID_dict['irrepairable']

        MI = pd.MultiIndex.from_tuples(MI_raw)

        SUMMARY = pd.DataFrame(np.empty((
            self._AIM_in['general']['realizations'],
            len(MI))), columns=MI)
        SUMMARY[:] = np.NaN

        # event time
        for prop in ['month', 'weekday?', 'hour']:
            offset = 0
            if prop == 'month':
                offset = 1
            SUMMARY.loc[:, ('event time', prop)] = \
                self._TIME.loc[:, prop] + offset

        # inhabitants
        if DVs['injuries']:
            SUMMARY.loc[:, ('inhabitants', '')] = self._POP.sum(axis=1)

        # reconstruction cost
        if DVs['rec_cost']:
            repl_cost = self._AIM_in['general']['replacement_cost']

            SUMMARY.loc[ncID, ('reconstruction', 'cost')] = \
                self._DV_dict['rec_cost'].sum(axis=1)
            #SUMMARY.loc[:, ('reconstruction', 'cost')] *= repl_cost

        # reconstruction time
        if DVs['rec_time']:
            SUMMARY.loc[ncID, ('reconstruction', 'time')] = \
                self._DV_dict['rec_time'].sum(axis=1)

        # injuries
        if DVs['injuries']:
            for sev_id in range(4):
                sev_tag = 'sev. {}'.format(sev_id+1)
                SUMMARY.loc[ncID, ('injuries', sev_tag)] = \
                    self._DV_dict['injuries'][sev_id].sum(axis=1)

        self._SUMMARY = SUMMARY.dropna(axis=1, how='all')

    def save_outputs(self, *args, **kwargs):
        """

        Returns
        -------

        """
        super(HAZUS_Assessment, self).save_outputs(*args, **kwargs)

    def _create_correlation_matrix(self, rho_target, c_target=-1,
                                   include_CSG=False,
                                   include_DSG=False, include_DS=False):
        """

        Parameters
        ----------
        rho_target
        c_target
        include_CSG
        include_DSG
        include_DS

        Returns
        -------

        """

        # set the correlation structure
        rho_FG, rho_PG, rho_LOC, rho_DIR, rho_CSG, rho_DS = np.zeros(6)

        if rho_target in ['FG', 'PG', 'DIR', 'LOC', 'CSG', 'ATC', 'DS']:
            rho_DS = 1.0
        if rho_target in ['FG', 'PG', 'DIR', 'LOC', 'CSG']:
            rho_CSG = 1.0
        if rho_target in ['FG', 'PG', 'DIR']:
            rho_DIR = 1.0
        if rho_target in ['FG', 'PG', 'LOC']:
            rho_LOC = 1.0
        if rho_target in ['FG', 'PG']:
            rho_PG = 1.0
        if rho_target == 'FG':
            rho_FG = 1.0

        L_D_list = []
        dims = []
        DS_list = []
        ATC_rho = []
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id, c_name in enumerate(s_fg_keys):
            comp = self._FG_in[c_name]

            if ((c_target == -1) or (c_id == c_target)):
                c_L_D_list = []
                c_DS_list = []
                ATC_rho.append(comp['correlation'])

                if include_DSG:
                    DS_count = 0
                    s_dsg_keys = sorted(comp['DSG_set'].keys())
                    for dsg_i in s_dsg_keys:
                        DSG = comp['DSG_set'][dsg_i]
                        if include_DS:
                            DS_count += len(DSG['DS_set'])
                        else:
                            DS_count += 1
                else:
                    DS_count = 1

                #for loc in comp['locations']:
                #    if include_CSG:
                #        u_dirs = comp['directions']
                #    else:
                #        u_dirs = np.unique(comp['directions'])
                #    c_L_D_list.append([])
                #    for dir_ in u_dirs:
                #        c_DS_list.append(DS_count)
                #        for ds_i in range(DS_count):
                #            c_L_D_list[-1].append(dir_)

                for loc_u in np.unique(comp['locations']):
                    c_L_D_list.append([])
                    for loc, dir, csg_weights in zip(comp['locations'],
                                                     comp['directions'],
                                                     comp['csg_weights']):
                        if loc == loc_u:
                            if include_CSG:
                                csg_list = csg_weights
                            else:
                                csg_list = [1.0,]
                            for csg_ in csg_list:
                                c_DS_list.append(DS_count)
                                for ds_i in range(DS_count):
                                    c_L_D_list[-1].append(dir)

                c_dims = sum([len(loc) for loc in c_L_D_list])
                dims.append(c_dims)
                L_D_list.append(c_L_D_list)
                DS_list.append(c_DS_list)

        rho = np.ones((sum(dims), sum(dims))) * rho_FG

        f_pos_id = 0
        for c_id, (c_L_D_list, c_dims, c_DS_list) in enumerate(
            zip(L_D_list, dims, DS_list)):
            c_rho = np.ones((c_dims, c_dims)) * rho_PG

            # dependencies btw directions
            if rho_DIR != 0:
                c_pos_id = 0
                for loc_D_list in c_L_D_list:
                    l_dim = len(loc_D_list)
                    c_rho[c_pos_id:c_pos_id + l_dim,
                    c_pos_id:c_pos_id + l_dim] = rho_DIR
                    c_pos_id = c_pos_id + l_dim

            # dependencies btw locations
            if rho_LOC != 0:
                flat_dirs = []
                [[flat_dirs.append(dir_i) for dir_i in dirs] for dirs in
                 c_L_D_list]
                flat_dirs = np.array(flat_dirs)
                for u_dir in np.unique(flat_dirs):
                    dir_ids = np.where(flat_dirs == u_dir)[0]
                    for i in dir_ids:
                        for j in dir_ids:
                            c_rho[i, j] = rho_LOC

            if ((rho_CSG != 0) or (rho_target == 'ATC')):
                c_pos_id = 0
                if rho_target == 'ATC':
                    rho_to_use = float(ATC_rho[c_id])
                else:
                    rho_to_use = rho_CSG
                for loc_D_list in c_L_D_list:
                    flat_dirs = np.array(loc_D_list)
                    for u_dir in np.unique(flat_dirs):
                        dir_ids = np.where(flat_dirs == u_dir)[0]
                        for i in dir_ids:
                            for j in dir_ids:
                                c_rho[c_pos_id + i, c_pos_id + j] = rho_to_use
                    c_pos_id = c_pos_id + len(loc_D_list)

            if rho_DS != 0:
                c_pos_id = 0
                for l_dim in c_DS_list:
                    c_rho[c_pos_id:c_pos_id + l_dim,
                          c_pos_id:c_pos_id + l_dim] = rho_DS
                    c_pos_id = c_pos_id + l_dim

            rho[f_pos_id:f_pos_id + c_dims,
                f_pos_id:f_pos_id + c_dims] = c_rho
            f_pos_id = f_pos_id + c_dims

        np.fill_diagonal(rho, 1.0)

        return rho

    def _create_RV_quantities(self, rho_qnt):
        """

        Parameters
        ----------
        rho_qnt

        Returns
        -------

        """

        q_theta, q_sig, q_tag, q_dist = [np.array([]) for i in range(4)]

        # collect the parameters for each quantity dimension
        s_fg_keys = sorted(self._FG_in.keys())
        for c_id in s_fg_keys:
            comp = self._FG_in[c_id]

            u_dirs = np.unique(comp['directions'])

            #dir_weights = comp['dir_weights']
            #theta_list = []
            #[[theta_list.append(qnt * dw)
            #  for dw in dir_weights] for qnt in comp['quantities']]

            theta_list = comp['quantities']
            q_theta = np.append(q_theta, theta_list)

            dist_list = comp['distribution_kind']
            q_dist = np.append(q_dist, dist_list)

            cov_list = comp['cov']
            for theta, dk, cov in list(zip(theta_list, dist_list, cov_list)):
                if dk == 'normal':
                    q_sig = np.append(q_sig, [cov*theta,])
                else:
                    q_sig = np.append(q_sig, [cov, ])

            q_tag = np.append(q_tag, [c_id + '-QNT-' + str(s_i) + '-' + str(d_i)
                                      for s_i, d_i
                                      in list(zip(comp['locations'],
                                                  comp['directions']))])
        dims = len(q_theta)
        rho = self._create_correlation_matrix(rho_qnt)
        q_COV = np.outer(q_sig, q_sig) * rho

        # add lower limits to ensure only positive quantities
        # zero is probably too low, and it might make sense to introduce upper
        # limits as well
        tr_lower = [0. for d in range(dims)]
        tr_upper = [None for d in range(dims)]
        # to avoid truncations affecting other dimensions when rho_QNT is large,
        # assign a post-truncation correlation structure
        corr_ref = 'post'

        # create a random variable for component quantities in performance groups
        if q_tag.size > 0:
            quantity_RV = RandomVariable(ID=100,
                                         dimension_tags=q_tag,
                                         distribution_kind=q_dist,
                                         theta=q_theta,
                                         COV=q_COV,
                                         truncation_limits=[tr_lower, tr_upper],
                                         corr_ref=corr_ref)
        else:
            quantity_RV = None

        return quantity_RV

    def _create_RV_fragilities(self, c_id, comp, rho_fr):
        """

        Parameters
        ----------
        c_id
        comp
        rho_fr

        Returns
        -------

        """

        # prepare the basic multivariate distribution data for one component subgroup considering all damage states
        d_theta, d_sig, d_tag, d_distr_kind = [np.array([]) for i in range(4)]

        s_dsg_keys = sorted(comp['DSG_set'].keys())
        for d_id in s_dsg_keys:
            DSG = comp['DSG_set'][d_id]
            d_theta = np.append(d_theta, DSG['theta'])
            d_sig = np.append(d_sig, DSG['sig'])
            d_tag = np.append(d_tag, comp['ID'] + '-' + str(d_id))
            d_distr_kind = np.append(d_distr_kind, DSG['distribution_kind'])
        dims = len(d_theta)

        # get the total number of random variables for this fragility group
        # TODO: add the possibility of multiple locations and directions
        #rv_count = len(comp['locations']) * len(comp['directions']) * dims
        rv_count = sum([len(csg_w) for csg_w in comp['csg_weights']]) * dims

        # create the (empty) input arrays for the RV
        c_theta = np.zeros(rv_count)
        c_tag = np.empty(rv_count, dtype=object)
        c_sig = np.zeros(rv_count)
        c_distr_kind = np.empty(rv_count, dtype=object)

        pos_id = 0
        #for l_id in comp['locations']:
        #    # for each location-direction pair)
        #    for d_id, __ in enumerate(comp['directions']):
        #        # for each component-subgroup
        #        c_theta[pos_id:pos_id + dims] = d_theta
        #        c_sig[pos_id:pos_id + dims] = d_sig
        #        c_tag[pos_id:pos_id + dims] = [
        #            t + '-LOC-{}-CSG-{}'.format(l_id, d_id) for t in d_tag]
        #        c_distr_kind[pos_id:pos_id + dims] = d_distr_kind
        #        pos_id += dims

        for l_id, d_id, csg_list in zip(comp['locations'], comp['directions'],
                                        comp['csg_weights']):
            # for each location-direction pair)
            for csg_id, __ in enumerate(csg_list):
                # for each component-subgroup
                c_theta[pos_id:pos_id + dims] = d_theta
                c_sig[pos_id:pos_id + dims] = d_sig
                c_tag[pos_id:pos_id + dims] = [
                    t + '-LOC-{}-DIR-{}-CSG-{}'.format(l_id, d_id, csg_id)
                    for t in d_tag]
                c_distr_kind[pos_id:pos_id + dims] = d_distr_kind
                pos_id += dims

        # create the covariance matrix
        #c_rho = self._create_correlation_matrix(rho_fr, c_target=c_id,
        #                                        include_DSG=True,
        #                                        include_CSG=True)
        c_rho = np.ones((rv_count, rv_count))
        c_COV = np.outer(c_sig, c_sig) * c_rho

        if c_tag.size > 0:
            fragility_RV = RandomVariable(ID=300 + c_id,
                                          dimension_tags=c_tag,
                                          distribution_kind=c_distr_kind,
                                          theta=c_theta,
                                          COV=c_COV)
        else:
            fragility_RV = None

        return fragility_RV

    def _create_fragility_groups(self):

        RVd = self._RV_dict
        DVs = self._AIM_in['decision_variables']

        # use the building replacement cost to calculate the absolute
        # reconstruction cost for component groups
        repl_cost = self._AIM_in['general']['replacement_cost']

        # create a list for the fragility groups
        FG_dict = dict()

        s_fg_keys = sorted(self._FG_in.keys())
        for c_id in s_fg_keys:
            comp = self._FG_in[c_id]

            FG_ID = len(FG_dict.keys()) + 1

            # create a list for the performance groups
            performance_groups = []

            # one group for each of the stories prescribed by the user
            PG_locations = comp['locations']
            PG_directions = comp['directions']
            PG_csg_lists = comp['csg_weights']
            for loc, dir_, csg_list in zip(PG_locations, PG_directions,
                                           PG_csg_lists):
                PG_ID = 10000 * FG_ID + 10 * loc + dir_

                # get the quantity
                #QNT = None
                QNT = RandomVariableSubset(
                    RVd['QNT'],
                    tags=[c_id + '-QNT-' + str(loc) + '-' + str(dir_), ])

                # create the damage objects
                # consequences are calculated on a performance group level

                # create a list for the damage state groups and their tags
                DSG_list = []
                d_tags = []
                s_dsg_keys = sorted(comp['DSG_set'].keys())
                for dsg_i, DSG_ID in enumerate(s_dsg_keys):
                    DSG = comp['DSG_set'][DSG_ID]
                    d_tags.append(c_id + '-' + DSG_ID)

                    # create a list for the damage states
                    DS_set = []

                    s_ds_keys = sorted(DSG['DS_set'].keys())
                    for ds_i, DS_ID in enumerate(s_ds_keys):
                        DS = DSG['DS_set'][DS_ID]

                        # create the consequence functions
                        # note: consequences in HAZUS are conditioned on
                        # damage with no added uncertainty

                        if DVs['rec_cost']:
                            data = DS['repair_cost']
                            f_median = prep_constant_median_DV(data*repl_cost)
                            CF_cost = ConsequenceFunction(
                                DV_median=f_median,
                                DV_distribution=None)
                        else:
                            CF_cost = None

                        if DVs['rec_time'] and ('repair_time' in DS.keys()):
                            data = DS['repair_time']
                            f_median = prep_constant_median_DV(data)
                            CF_time = ConsequenceFunction(
                                DV_median=f_median,
                                DV_distribution=None)
                        else:
                            CF_time = None

                        # note: no red tag in HAZUS assessments

                        if (DVs['injuries']) and ('injuries' in DS.keys()):
                            CF_inj_set = []
                            for inj_i, theta in enumerate(
                                DS['injuries']):
                                if theta > 0.:
                                    f_median = prep_constant_median_DV(
                                        theta)
                                    CF_inj_set.append(ConsequenceFunction(
                                        DV_median=f_median,
                                        DV_distribution=None))
                                else:
                                    CF_inj_set.append(None)
                        else:
                            CF_inj_set = [None, ]

                        DS_set.append(DamageState(ID=ds_i + 1,
                                                  description=DS[
                                                      'description'],
                                                  weight=DS['weight'],
                                                  repair_cost_CF=CF_cost,
                                                  reconstruction_time_CF=CF_time,
                                                  injuries_CF_set=CF_inj_set
                                                  ))

                    # add the DSG to the list
                    DSG_list.append(DamageStateGroup(ID=dsg_i + 1,
                                                     DS_set=DS_set,
                                                     DS_set_kind=DSG[
                                                         'DS_set_kind']
                                                     ))

                # create the fragility functions
                FF_set = []
                #CSG_this = np.where(comp['directions'] == dir_)[0]
                #PG_weights = np.asarray(comp['csg_weights'])[CSG_this]
                # normalize the weights
                #PG_weights /= sum(PG_weights)
                for csg_id, __ in enumerate(csg_list):
                    # assign the appropriate random variable to the fragility
                    # function
                    ff_tags = [t + '-LOC-{}-DIR-{}-CSG-{}'.format(loc, dir_,
                                                                  csg_id)
                               for t in d_tags]
                    EDP_limit = RandomVariableSubset(RVd['FR-' + c_id],
                                                     tags=ff_tags)
                    FF_set.append(FragilityFunction(EDP_limit))

                # create the performance group
                PG = PerformanceGroup(ID=PG_ID,
                                      location=loc,
                                      quantity=QNT,
                                      fragility_functions=FF_set,
                                      DSG_set=DSG_list,
                                      csg_weights=csg_list,
                                      direction=dir_
                                      )
                performance_groups.append(PG)

            # create the fragility group
            FG = FragilityGroup(ID=FG_ID,
                                #kind=comp['kind'],
                                demand_type=comp['demand_type'],
                                performance_groups=performance_groups,
                                directional=comp['directional'],
                                correlation=comp['correlation'],
                                demand_location_offset=comp['offset'],
                                incomplete=comp['incomplete'],
                                name=str(FG_ID) + ' - ' + comp['ID'],
                                description=comp['description']
                                )

            FG_dict.update({comp['ID']: FG})

        return FG_dict

    def _sample_event_time(self):

        sample_count = self._AIM_in['general']['realizations']

        # month - uniform distribution over [0,11]
        month = np.random.randint(0, 12, size=sample_count)

        # weekday - binomial with p=5/7
        weekday = np.random.binomial(1, 5. / 7., size=sample_count)

        # hour - uniform distribution over [0,23]
        hour = np.random.randint(0, 24, size=sample_count)

        data = pd.DataFrame(data={'month'   : month,
                                  'weekday?': weekday,
                                  'hour'    : hour},
                            dtype=int)

        return data

    def _get_population(self):
        """
        Use the population characteristics to generate random population samples.

        Returns
        -------

        """
        POPin = self._POP_in
        TIME = self._TIME

        POP = pd.DataFrame(
            np.ones((len(TIME.index), len(POPin['peak']))) * POPin['peak'],
            columns=['LOC' + str(loc + 1)
                     for loc in range(len(POPin['peak']))])

        weekdays = TIME[TIME['weekday?'] == 1].index
        weekends = TIME[~TIME.index.isin(weekdays)].index

        for col in POP.columns.values:
            POP.loc[weekdays, col] = (
                POP.loc[weekdays, col] *
                np.array(POPin['weekday']['daily'])[
                    TIME.loc[weekdays, 'hour'].values.astype(int)] *
                np.array(POPin['weekday']['monthly'])[
                    TIME.loc[weekdays, 'month'].values.astype(int)])

            POP.loc[weekends, col] = (
                POP.loc[weekends, col] *
                np.array(POPin['weekend']['daily'])[
                    TIME.loc[weekends, 'hour'].values.astype(int)] *
                np.array(POPin['weekend']['monthly'])[
                    TIME.loc[weekends, 'month'].values.astype(int)])

        return POP

    def _calc_damage(self):

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)
        DMG = pd.DataFrame()

        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = []
            for DSG in PG_set[0]._DSG_set:
                for DS in DSG._DS_set:
                    DS_list.append(str(DSG._ID) + '-' + str(DS._ID))
            d_count = len(DS_list)

            MI = pd.MultiIndex.from_product([[FG._ID, ],
                                             [pg._ID for pg in PG_set],
                                             DS_list],
                                            names=['FG', 'PG', 'DS'])

            FG_damages = pd.DataFrame(np.zeros((NC_samples, len(MI))),
                                      columns=MI,
                                      index=ncID)

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID
                if PG._quantity is not None:
                    PG_qnt = PG._quantity.samples.loc[ncID]
                else:
                    PG_qnt = pd.DataFrame(np.ones(NC_samples),index=ncID)

                # get the corresponding demands                 
                if not FG._directional:
                    demand_ID_list = []

                    for demand_ID in self._EDP_dict.keys():
                        if demand_ID[:3] == FG._demand_type:
                            demand_data = demand_ID.split('-')
                            if int(demand_data[2]) == PG._location + FG._demand_location_offset:
                                demand_ID_list.append(demand_ID)                            

                    EDP_samples = self._EDP_dict[demand_ID_list[0]].samples.loc[ncID]
                    if len(demand_ID_list)>1:
                        for demand_ID in demand_ID_list[1:]:
                            new_samples = self._EDP_dict[demand_ID].samples.loc[ncID]                            
                            EDP_samples = np.maximum(new_samples.values,
                                                     EDP_samples.values)

                else:
                    demand_ID = (FG._demand_type +
                             '-LOC-' + str(PG._location + FG._demand_location_offset) +
                             '-DIR-' + str(PG._direction))

                    if demand_ID in self._EDP_dict.keys():
                        EDP_samples = self._EDP_dict[demand_ID].samples.loc[ncID]
                    else:
                        # If the required demand is not available, then we are most
                        # likely analyzing a 3D structure using results from a 2D
                        # simulation. The best thing we can do in that particular
                        # case is to use the EDP from the 1 direction for all other
                        # directions.
                        demand_ID = (FG._demand_type +
                                     '-LOC-' + str(PG._location + FG._demand_location_offset) + '-DIR-1')
                        EDP_samples = self._EDP_dict[demand_ID].samples.loc[ncID]

                csg_w_list = np.array(PG._csg_weights)
                for csg_i, csg_w in enumerate(csg_w_list):
                    DSG_df = PG._FF_set[csg_i].DSG_given_EDP(EDP_samples)

                    for DSG in PG._DSG_set:
                        in_this_DSG = DSG_df[DSG_df.values == DSG._ID].index
                        if DSG._DS_set_kind == 'single':
                            DS = DSG._DS_set[0]
                            DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                            FG_damages.loc[in_this_DSG,
                                           (FG._ID, PG_ID, DS_tag)] += csg_w
                        elif DSG._DS_set_kind == 'mutually exclusive':
                            DS_weights = [DS._weight for DS in DSG._DS_set]
                            DS_RV = RandomVariable(
                                ID=-1, dimension_tags=['me_DS', ],
                                distribution_kind='multinomial',
                                p_set=DS_weights)
                            DS_df = DS_RV.sample_distribution(
                                len(in_this_DSG)) + 1
                            for DS in DSG._DS_set:
                                DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                                in_this_DS = DS_df[DS_df.values == DS._ID].index
                                FG_damages.loc[in_this_DSG[in_this_DS],
                                               (FG._ID, PG_ID, DS_tag)] += csg_w
                        elif DSG._DS_set_kind == 'simultaneous':
                            DS_weights = [DS._weight for DS in DSG._DS_set]
                            DS_df = np.random.uniform(
                                size=(len(in_this_DSG), len(DS_weights)))
                            which_DS = DS_df < DS_weights
                            any_DS = np.any(which_DS, axis=1)
                            no_DS_ids = np.where(any_DS == False)[0]

                            while len(no_DS_ids) > 0:
                                DS_df_add = np.random.uniform(
                                    size=(len(no_DS_ids), len(DS_weights)))
                                which_DS_add = DS_df_add < DS_weights
                                which_DS[no_DS_ids] = which_DS_add

                                any_DS = np.any(which_DS_add, axis=1)
                                no_DS_ids = no_DS_ids[
                                    np.where(any_DS == False)[0]]

                            for ds_i, DS in enumerate(DSG._DS_set):
                                DS_tag = str(DSG._ID) + '-' + str(DS._ID)
                                in_this_DS = which_DS[:, ds_i]
                                FG_damages.loc[in_this_DSG[in_this_DS], (
                                    FG._ID, PG_ID, DS_tag)] += csg_w

                        else:
                            raise ValueError(
                                "Unknown damage state type: {}".format(
                                    DSG._DS_set_kind)
                            )

                FG_damages.iloc[:, pg_i * d_count:(pg_i + 1) * d_count] = \
                    FG_damages.mul(PG_qnt.iloc[:, 0], axis=0)

            DMG = pd.concat((DMG, FG_damages), axis=1)

        DMG.index = ncID

        # sort the columns to enable index slicing later
        DMG = DMG.sort_index(axis=1, ascending=True)

        return DMG

    def _calc_repair_cost_and_time(self):

        idx = pd.IndexSlice
        DVs = self._AIM_in['decision_variables']

        DMG_by_FG_and_DS = self._DMG.groupby(level=[0, 2], axis=1).sum()

        repID = self._ID_dict['repairable']
        REP_samples = len(repID)
        DV_COST = pd.DataFrame(np.zeros((REP_samples, len(self._DMG.columns))),
                               columns=self._DMG.columns, index=repID)
        DV_TIME = deepcopy(DV_COST)

        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = self._DMG.loc[:, idx[FG._ID, PG_set[0]._ID, :]].columns
            DS_list = DS_list.levels[2][DS_list.codes[2]].values

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID

                for d_i, d_tag in enumerate(DS_list):
                    dsg_i = int(d_tag[0]) - 1
                    ds_i = int(d_tag[-1]) - 1

                    DS = PG._DSG_set[dsg_i]._DS_set[ds_i]

                    TOT_qnt = DMG_by_FG_and_DS.loc[repID, (FG._ID, d_tag)]
                    PG_qnt = self._DMG.loc[repID,
                                           (FG._ID, PG_ID, d_tag)]

                    # repair cost
                    if DVs['rec_cost']:
                        COST_samples = DS.unit_repair_cost(quantity=TOT_qnt)
                        if COST_samples is not None:
                            DV_COST.loc[:,
                            (FG._ID, PG_ID, d_tag)] = COST_samples * PG_qnt

                    if DVs['rec_time']:
                        # repair time
                        TIME_samples = DS.unit_reconstruction_time(
                            quantity=TOT_qnt)
                        if TIME_samples is not None:
                            DV_TIME.loc[:,
                            (FG._ID, PG_ID, d_tag)] = TIME_samples * PG_qnt

        # sort the columns to enable index slicing later
        if DVs['rec_cost']:
            DV_COST = DV_COST.sort_index(axis=1, ascending=True)
        else:
            DV_COST = None
        if DVs['rec_time']:
            DV_TIME = DV_TIME.sort_index(axis=1, ascending=True)
        else:
            DV_TIME = None

        return DV_COST, DV_TIME

    def _calc_non_collapse_injuries(self):

        idx = pd.IndexSlice

        ncID = self._ID_dict['non-collapse']
        NC_samples = len(ncID)
        DV_INJ_dict = dict([(i, pd.DataFrame(np.zeros((NC_samples,
                                                       len(self._DMG.columns))),
                                             columns=self._DMG.columns,
                                             index=ncID))
                            for i in range(self._inj_lvls)])
        s_fg_keys = sorted(self._FG_dict.keys())
        for fg_id in s_fg_keys:
            FG = self._FG_dict[fg_id]

            PG_set = FG._performance_groups

            DS_list = self._DMG.loc[:, idx[FG._ID, PG_set[0]._ID, :]].columns
            DS_list = DS_list.levels[2][DS_list.codes[2]].values

            for pg_i, PG in enumerate(PG_set):

                PG_ID = PG._ID

                for d_i, d_tag in enumerate(DS_list):
                    dsg_i = int(d_tag[0]) - 1
                    ds_i = int(d_tag[-1]) - 1

                    DS = PG._DSG_set[dsg_i]._DS_set[ds_i]

                    P_affected = self._POP.loc[ncID]

                    QNT = self._DMG.loc[:, (FG._ID, PG_ID, d_tag)]

                    # estimate injuries
                    for i in range(self._inj_lvls):
                        INJ_samples = DS.unit_injuries(severity_level=i,
                                                       sample_size=NC_samples)
                        if INJ_samples is not None:
                            P_aff_i = P_affected.loc[:,
                                      'LOC{}'.format(PG._location)]
                            INJ_i = INJ_samples * P_aff_i * QNT
                            DV_INJ_dict[i].loc[:,
                            (FG._ID, PG_ID, d_tag)] = INJ_i

        # remove the useless columns from DV_INJ
        for i in range(self._inj_lvls):
            DV_INJ = DV_INJ_dict[i]
            DV_INJ_dict[i] = DV_INJ.loc[:, (DV_INJ != 0.0).any(axis=0)]

        # sort the columns to enable index slicing later
        for i in range(self._inj_lvls):
            DV_INJ_dict[i] = DV_INJ_dict[i].sort_index(axis=1, ascending=True)

        return DV_INJ_dict