#!/usr/bin/env python
"""
run_1yr_fullchem_benchmark.py: Driver script for creating benchmark plots and
                               testing gcpy 1-year full-chemistry benchmark
                               capability.

Run this script to generate benchmark comparisons between:

    (1) GCC (aka GEOS-Chem "Classic") vs. GCC
    (2) GCHP vs GCC (not yet tested)
    (3) GCHP vs GCHP (not yet tested)

You can customize this by editing the following settings in the
"Configurables" section below:

    (1) Edit the path variables so that they point to folders w/ model data
    (2) Edit the version strings for each benchmark simulation
    (3) Edit the switches that turn on/off creating of plots and tables
    (4) If necessary, edit labels for the dev and ref versions

Calling sequence:

    ./run_1yr_fullchem_benchmark.py

To test gcpy, copy this script anywhere you want to run the test and
set gcpy_test to True at the top of the script. Benchmark artifacts will
be created locally in new folder called Plots.

Remarks:

    By default, matplotlib will try to open an X window for plotting.
    If you are running this script in an environment where you do not have
    an active X display (such as in a computational queue), then you will
    need to use these commands to disable the X-window functionality.

        import os
        os.environ["QT_QPA_PLATFORM"]="offscreen"

    For more information, please see this issue posted at the ipython site:

        https://github.com/ipython/ipython/issues/10627

    This issue might be fixed in matplotlib 3.0.
"""

# =====================================================================
# Imports and global settings (you should not need to edit these)
# =====================================================================

import os
from os.path import join
import warnings

from calendar import monthrange
import numpy as np
import xarray as xr

from gcpy import benchmark as bmk
from gcpy.core import get_filepath, get_filepaths
import gcpy.ste_flux as ste
import gcpy.budget_aer as aerbdg
import gcpy.budget_ops as opbdg
import gcpy.mean_oh_from_logs as moh

# Tell matplotlib not to look for an X-window
os.environ["QT_QPA_PLATFORM"]="offscreen"

# Suppress harmless run-time warnings (mostly about underflow in division)
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

# This script has a fixed benchmark type
bmk_type     = "FullChemBenchmark"
bmk_year     = '2016'
bmk_mon_strs = ["Jan", "Apr", "Jul", "Oct"]
bmk_mon_inds = [0, 3, 6, 9]

########################################################################
###           CONFIGURABLE SETTINGS: ***EDIT AS NEEDED ***           ###
########################################################################

# =====================================================================
# Benchmark information
# Note: When doing GCHP vs GCC comparisions gchp_dev will be compared
# to gcc_dev (not gcc_ref!).
# =====================================================================

# High-level directory containing subdirectories with data
maindir  = "/n/holyscratch01/external_repos/GEOS-CHEM/gcgrid/geos-chem/validation/gcpy_test_data/1yr_fullchem"

# Version strings
# NOTE: these will be used in some filenames and so should not have spaces
# or other characters not appropriate for a filename.
gcc_ref_version = "GCC_ref"
gcc_dev_version = "GCC_dev"
gchp_ref_version = "GCHP_ref"
gchp_dev_version = "GCHP_dev"

# Path to regridding weights
weightsdir = "/n/holylfs/EXTERNAL_REPOS/GEOS-CHEM/gcgrid/gcdata/ExtData/GCHP/RegriddingWeights"

# =====================================================================
# Specify if this is a gcpy test validation run
# =====================================================================
gcpy_test = True

# =====================================================================
# Comparisons to run 
# =====================================================================
gcc_vs_gcc   = True
gchp_vs_gcc  = True # not yet tested
gchp_vs_gchp = True # not yet tested
# GCHP vs GCC diff of diffs not included in 1-yr full chemistry benchmark

# =====================================================================
# Output to generate (plots/tables will be created in this order):
# =====================================================================
plot_conc    = False
plot_emis    = False
emis_table   = True
plot_jvalues = False
plot_aod     = False
mass_table   = True
ops_budget_table = True
aer_budget_table = True
ste_table    = True
OH_metrics   = True

# Plot concentrations and emissions by category?
plot_by_spc_cat = True
plot_by_hco_cat = True

# =====================================================================
# Data directories
# For gchp_vs_gcc_refdir use gcc_dev_version, not ref (mps, 6/27/19)
# =====================================================================

# Diagnostics file directory paths
gcc_vs_gcc_refdir      = join(maindir, gcc_ref_version,  "OutputDir")
gcc_vs_gcc_devdir      = join(maindir, gcc_dev_version,  "OutputDir")
gchp_vs_gcc_refdir     = join(maindir, gcc_dev_version,  "OutputDir")
gchp_vs_gcc_devdir     = join(maindir, gchp_dev_version, "OutputDir")
gchp_vs_gchp_refdir    = join(maindir, gchp_ref_version, "OutputDir")
gchp_vs_gchp_devdir    = join(maindir, gchp_dev_version, "OutputDir")

# Restart file directory paths
gcc_vs_gcc_refrstdir   = join(maindir, gcc_ref_version,  "restarts")
gcc_vs_gcc_devrstdir   = join(maindir, gcc_dev_version,  "restarts")
gchp_vs_gcc_refrstdir  = join(maindir, gcc_dev_version,  "restarts")
gchp_vs_gcc_devrstdir  = join(maindir, gchp_dev_version)
gchp_vs_gchp_refrstdir = join(maindir, gchp_ref_version)
gchp_vs_gchp_devrstdir = join(maindir, gchp_dev_version)

# Log file directories -- GEOS-Chem "Classic" only
gcc_vs_gcc_reflogdir   = join(maindir, gcc_ref_version,  "logs")
gcc_vs_gcc_devlogdir   = join(maindir, gcc_dev_version,  "logs")

# Plots directories
if gcpy_test:
    mainplotsdir          = './Plots'
    gcc_vs_gcc_plotsdir    = join(mainplotsdir,'GCC_version_comparison')
    gchp_vs_gchp_plotsdir  = join(mainplotsdir,'GCHP_version_comparison')
    gchp_vs_gcc_plotsdir   = join(mainplotsdir,'GCHP_GCC_comparison')
    if not os.path.exists(mainplotsdir): os.mkdir(mainplotsdir)
else:
    gcc_vs_gcc_plotsdir    = join(maindir, gcc_dev_version, "Plots")
    gchp_vs_gchp_plotsdir  = join(maindir, gchp_dev_version,
                              "Plots", "GCHP_version_comparison")
    gchp_vs_gcc_plotsdir   = join(maindir, gchp_dev_version,
                              "Plots", "GCHP_GCC_comparison")

# Tables directories
gcc_vs_gcc_tablesdir   = join(gcc_vs_gcc_plotsdir,"Tables") 
gchp_vs_gcc_tablesdir  = join(gchp_vs_gcc_plotsdir,"Tables") 
gchp_vs_gchp_tablesdir = join(gchp_vs_gchp_plotsdir,"Tables")

# Budget directories
gcc_vs_gcc_budgetdir   = join(gcc_vs_gcc_plotsdir,"Budget") 
gchp_vs_gcc_budgetdir  = join(gchp_vs_gcc_plotsdir,"Budget") 
gchp_vs_gchp_budgetdir = join(gchp_vs_gchp_plotsdir,"Budget")

# =====================================================================
# Plot title strings
# For gchp_vs_gcc_refstr use gcc_dev_version, not ref (mps, 6/27/19)
# =====================================================================
gcc_vs_gcc_refstr    = gcc_ref_version
gcc_vs_gcc_devstr    = gcc_dev_version
gchp_vs_gcc_refstr   = gcc_dev_version
gchp_vs_gcc_devstr   = gchp_dev_version
gchp_vs_gchp_refstr  = gchp_ref_version
gchp_vs_gchp_devstr  = gchp_dev_version

########################################################################
###    THE REST OF THESE SETTINGS SHOULD NOT NEED TO BE CHANGED      ###
########################################################################

# =====================================================================
# Dates and times
# =====================================================================

# Month/year strings for use in table subdirectories (e.g. Jan2016)
bmk_mon_yr_strs = [v + bmk_year for v in bmk_mon_strs]

# Get all months array of start datetimes for benchmark year
bmk_start = np.datetime64(bmk_year+"-01-01")
bmk_end = np.datetime64("{}-01-01".format(int(bmk_year)+1))
all_months = np.arange(bmk_start, bmk_end, step=np.timedelta64(1, "M"),
                       dtype="datetime64[M]")

# Get all months array of mid-point datetime per month for benchmark year
# and # sec per month
# NOTE: GCHP time-averaged files have time in the middle of the month
sec_per_month = np.zeros(12)
all_months_mid = np.zeros(12, dtype="datetime64[h]")
for m in range(12):
    days_in_mon = monthrange(int(bmk_year), m + 1)[1]
    sec_per_month[m-1] = days_in_mon * 86400.0
    middle_hr = int(days_in_mon*24/2)
    delta = np.timedelta64(middle_hr, 'h')
    all_months_mid[m] = all_months[m].astype("datetime64[h]") + delta

# Get subset of month datetimes for only benchmark months
bmk_mons = all_months[bmk_mon_inds]
bmk_mons_mid = all_months_mid[bmk_mon_inds]
bmk_sec_per_month = sec_per_month[bmk_mon_inds]

# ======================================================================
# Print the list of plots & tables to the screen
# ======================================================================

print("The following plots and tables will be created for {}:".format(bmk_type))
if plot_conc:        print(" - Concentration plots")
if plot_emis:        print(" - Emissions plots")
if plot_jvalues:     print(" - J-values (photolysis rates) plots")
if plot_aod:         print(" - Aerosol optical depth plots")
if ops_budget_table: print(" - Operations budget tables")
if aer_budget_table: print(" - Aerosol budget/burden tables")
if emis_table:       print(" - Table of emissions totals by species and inventory")
if mass_table:       print(" - Table of species mass")
if OH_metrics:       print(" - Table of OH metrics")
if ste_table:        print(" - Table of strat-trop exchange")
print("Comparisons will be made for the following combinations:")
if gcc_vs_gcc:   print(" - GCC vs GCC")
if gchp_vs_gcc:  print(" - GCHP vs GCC")
if gchp_vs_gchp: print(" - GCHP vs GCHP")

# ======================================================================
# Create GCC vs GCC benchmark plots and tables
# ======================================================================

if gcc_vs_gcc:

    # --------------------------------------------------------------
    # GCC vs GCC Concentration plots
    #
    # Includes lumped species and separates by category if plot_by_spc_cat
    # is true; otherwise excludes lumped species and writes to one file.
    # --------------------------------------------------------------
    if plot_conc:
        print("\n%%% Creating GCC vs. GCC concentration plots %%%")

        # Diagnostic collections to read
        col = "SpeciesConc"
        colmet = "StateMet"

        # Create concentration plots for each benchmark month
        for s, bmk_mon in enumerate(bmk_mons):

            ref = get_filepath(gcc_vs_gcc_refdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devdir, col, bmk_mon)
            refmet = get_filepath(gcc_vs_gcc_refdir, colmet, bmk_mon)
            devmet = get_filepath(gcc_vs_gcc_devdir, colmet, bmk_mon)
            bmk.make_benchmark_conc_plots(
                ref,
                gcc_vs_gcc_refstr,
                dev,
                gcc_vs_gcc_devstr,
                refmet=refmet,
                devmet=devmet,
                dst=gcc_vs_gcc_plotsdir,
                subdst=bmk_mon_yr_strs[s],
                weightsdir=weightsdir,
                benchmark_type=bmk_type,
                plot_by_spc_cat=plot_by_spc_cat,
                overwrite=True
            )

    # --------------------------------------------------------------
    # GCC vs GCC emissions plots
    # --------------------------------------------------------------
    if plot_emis:
        print("\n%%% Creating GCC vs. GCC emissions plots %%%")

        # Diagnostic collections to read
        col = "Emissions"

        # Create concentration plots for each benchmark month
        for s, bmk_mon in enumerate(bmk_mons):

            ref = get_filepath(gcc_vs_gcc_refdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devdir, col, bmk_mon)
            bmk.make_benchmark_emis_plots(
                ref,
                gcc_vs_gcc_refstr,
                dev,
                gcc_vs_gcc_devstr,
                dst=gcc_vs_gcc_plotsdir,
                subdst=bmk_mon_yr_strs[s],
                weightsdir=weightsdir,
                plot_by_spc_cat=plot_by_spc_cat,
                plot_by_hco_cat=plot_by_hco_cat,
                overwrite=True
            )

    # --------------------------------------------------------------
    # GCC vs GCC tables of emission and inventory totals
    # --------------------------------------------------------------
    if emis_table:
        print("\n%%% Creating GCC vs. GCC emissions & inventory totals %%%")

        # Diagnostic collections to read
        col = "Emissions"
        ref = get_filepaths(gcc_vs_gcc_refdir, col, all_months)
        dev = get_filepaths(gcc_vs_gcc_devdir, col, all_months)

        # Create emissions table that spans entire year
        bmk.make_benchmark_emis_tables(
            ref,
            gcc_vs_gcc_refstr,
            dev,
            gcc_vs_gcc_devstr,
            dst=gcc_vs_gcc_plotsdir,
            interval=sec_per_month,
            overwrite=True
        )

    # --------------------------------------------------------------
    # GCC vs GCC J-value plots
    # --------------------------------------------------------------
    if plot_jvalues:
        print("\n%%% Creating GCC vs. GCC J-value plots %%%")

        # Diagnostic collections to read
        col = "JValues"

        # Create J-value plots for each benchmark month
        for s, bmk_mon in enumerate(bmk_mons):

            ref = get_filepath(gcc_vs_gcc_refdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devdir, col, bmk_mon)
            bmk.make_benchmark_jvalue_plots(
                ref,
                gcc_vs_gcc_refstr,
                dev,
                gcc_vs_gcc_devstr,
                dst=gcc_vs_gcc_plotsdir,
                subdst=bmk_mon_yr_strs[s],
                weightsdir=weightsdir,
                overwrite=True
            )

    # --------------------------------------------------------------
    # GCC vs. GCC column AOD plots
    # --------------------------------------------------------------
    if plot_aod:
        print("\n%%% Creating GCC vs. GCC column AOD plots %%%")

        # Diagnostic collections to read
        col = "Aerosols"

        # Create AOD plots for each benchmark month
        for s, bmk_mon in enumerate(bmk_mons):

            ref = get_filepath(gcc_vs_gcc_refdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devdir, col, bmk_mon)
            bmk.make_benchmark_aod_plots(
                ref,
                gcc_vs_gcc_refstr,
                dev,
                gcc_vs_gcc_devstr,
                dst=gcc_vs_gcc_plotsdir,
                subdst=bmk_mon_yr_strs[s],
                weightsdir=weightsdir,
                overwrite=True
            )

    # --------------------------------------------------------------
    # GCC vs GCC mass tables
    # --------------------------------------------------------------
    if mass_table:
        print("\n%%% Creating GCC vs. GCC mass tables %%%")

        # Diagnostic collections to read
        col = "Restart"

        # Create mass table for each benchmark month
        for s, bmk_mon in enumerate(bmk_mons):

            ref = get_filepath(gcc_vs_gcc_refrstdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devrstdir, col, bmk_mon)
            label = "at 01{}".format(bmk_mon_yr_strs[s])
            plot_dir = join(gcc_vs_gcc_tablesdir, bmk_mon_yr_strs[s])
            bmk.make_benchmark_mass_tables(
                ref,
                gcc_vs_gcc_refstr,
                dev,
                gcc_vs_gcc_devstr,
                dst=plot_dir,
                label=label,
                overwrite=True,
                subdst=bmk_mon_yr_strs[s]
            )

    # --------------------------------------------------------------
    # GCC vs GCC operations budgets tables
    # --------------------------------------------------------------
    if ops_budget_table:
        print("\n%%% Creating GCC vs. GCC operations budget tables %%%")

        # Diagnostic collections to read
        col = "Budget"

        # Create budget table for each benchmark month (ewl??)
        for s, bmk_mon in enumerate(bmk_mons):
            ref = get_filepath(gcc_vs_gcc_refdir, col, bmk_mon)
            dev = get_filepath(gcc_vs_gcc_devdir, col, bmk_mon)
            plot_dir = join(gcc_vs_gcc_budgetdir, bmk_mon_yr_strs[s])
            opbdg.make_operations_budget_table(
                gcc_ref_version,
                ref,
                gcc_dev_version,
                dev,
                bmk_type,
                dst=plot_dir,
                label=bmk_mon_yr_strs[s],
                interval=bmk_sec_per_month[s],
                overwrite=True
            )

    # --------------------------------------------------------------
    # GCC vs GCC aerosols budgets/burdens tables
    # --------------------------------------------------------------
    if aer_budget_table:
        print("\n%%% Creating GCC vs. GCC aerosols budget tables %%%")

        # Compute annual mean AOD budgets and aerosol burdens
        aerbdg.aerosol_budgets_and_burdens(
            gcc_dev_version,
            gcc_vs_gcc_devdir,
            bmk_year,
            dst=gcc_vs_gcc_tablesdir,
            overwrite=True
        )

    # --------------------------------------------------------------
    # GCC Strat-Trop Exchange
    # --------------------------------------------------------------
    if ste_table:
        print("\n%%% Creating GCC vs. GCC Strat-Trop Exchange table %%%")

        # Diagnostic collections to read (all 12 months)
        col = "AdvFluxVert"
        dev = get_filepaths(gcc_vs_gcc_devdir, col, all_months)

        # Compute monthly and annual average strat-trop exchange of O3
        ste.make_benchmark_ste_table(
            gcc_dev_version,
            dev,
            bmk_year,
            dst=gcc_vs_gcc_tablesdir,
            bmk_type=bmk_type,
            species=['O3'],
            overwrite=True
        )

    # --------------------------------------------------------------
    # GCC vs GCC Global mean OH, MCF Lifetime, CH4 Lifetime
    # --------------------------------------------------------------
    if OH_metrics:
        print("\n%%% Creating GCC vs. GCC OH metrics %%%")

        ####################################################################
        # NOTE: Need to better validate this routine
        # for now, use the mean OH from the log files (bmy, 3/12/20)
        ## Paths to data files
        #collections = ["ConcAfterChem", "StateMet"]
        #gcc_vs_gcc_reflist = get_filepaths(gcc_vs_gcc_refdir, collections,
        #                                   bmk_months)
        #gcc_vs_gcc_devlist = get_filepaths(gcc_vs_gcc_devdir, collections,
        #                                   bmk_months)
        #
        ## Create OH metrics table
        #bmk.make_benchmark_oh_metrics(gcc_vs_gcc_reflist,
        #                              gcc_vs_gcc_refstr,
        #                              gcc_vs_gcc_devlist,
        #                              gcc_vs_gcc_devstr,
        #                              dst=gcc_vs_gcc_tablesdir,
        #                              overwrite=True)
        #####################################################################

        # Compute mean OH from the log files
        # NOTE: Only works for GEOS-Chem "Classic" benchmarks!
        moh.make_benchmark_oh_from_logs(
            gcc_vs_gcc_reflogdir,
            gcc_vs_gcc_refstr,
            gcc_vs_gcc_devlogdir,
            gcc_vs_gcc_devstr,
            bmk_year,
            dst=gcc_vs_gcc_tablesdir,
            overwrite=True
        )

# Not done below here:
# ======================================================================
# Create GCHP vs GCC benchmark plots and tables
# ======================================================================

if gchp_vs_gcc:

    if plot_conc:
        print("\n%%% Skipping GCHP vs. GCC concentration plots %%%")

    if plot_emis:
        print("\n%%% Skipping GCHP vs. GCC emissions plots %%%")

    if emis_table:
        print("\n%%% Skipping GCHP vs. GCC emissions tables %%%")

    if plot_jvalues:
        print("\n%%% Skipping GCHP vs. GCC J-values plots %%%")

    if plot_aod:
        print("\n%%% Skipping GCHP vs. GCC AOD plots %%%")

    if mass_table:
        print("\n%%% Skipping GCHP vs. GCC mass tables %%%")

    if OH_metrics:
        print("\n%%% Skipping GCHP vs. GCC OH metrics %%%")

# =====================================================================
# Create GCHP vs GCHP benchmark plots and tables
# =====================================================================

if gchp_vs_gchp:

    if plot_conc:
        print("\n%%% Skipping GCHP vs. GCHP concentration plots %%%")

    if plot_emis:
        print("\n%%% Skipping GCHP vs. GCHP emissions plots %%%")

    if emis_table:
        print("\n%%% Skipping GCHP vs. GCHP emissions tables %%%")

    if plot_jvalues:
        print("\n%%% Skipping GCHP vs. GCHP J-values plots %%%")

    if plot_aod:
        print("\n%%% Skipping GCHP vs. GCHP AOD plots %%%")

    if mass_table:
        print("\n%%% Skipping GCHP vs. GCHP mass tables %%%")

    if OH_metrics:
        print("\n%%% Skipping GCHP vs. GCHP OH metrics %%%")

