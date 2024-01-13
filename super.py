'''
Christian Bunker
M^2QM at UF
October 2023

Use density matrix renormalization group (DMRG) code from Huanchen Zhai (block2)
to study a 1D array of localized spins interacting with itinerant electrons in a
nanowire. In spintronics, this system is of interest because elecrons can impart
angular momentum on the localized spins, exerting spin transfer torque (STT).
'''

import numpy as np
import matplotlib.pyplot as plt

import time
import json
import sys
import os
print(">>> PWD: ",os.getcwd());

##################################################################################
#### wrappers

def get_energy_fci(h1e, g2e, nelec, nroots=1, verbose=0):
    # convert from arrays to uhf instance
    mol_inst, uhf_inst = utils.arr_to_uhf(h1e, g2e, len(h1e), nelec, verbose = verbose);
    # fci solution
    E_fci, v_fci = utils.scf_FCI(mol_inst, uhf_inst, nroots);
    if(nroots>1): E_fci, v_fci = E_fci[0], v_fci[0];
    # ci object
    CI_inst = tdfci.CIObject(v_fci, len(h1e), nelec);
    return CI_inst, E_fci, uhf_inst;

def check_observables(the_sites,psi,eris_or_driver, none_or_mpo,block,the_time):
    print("Time = {:.2f}".format(the_time));
    if(not block):
        # check gd state energy
        check_E = tdfci.compute_obs(psi, eris_or_driver)
        print("Total energy (FCI) = {:.6f}".format(check_E));
        # site spins
        s0_eris = tddmrg.get_sz(len(eris_or_driver.h1e[0]), eris_or_driver, the_sites[0], block);
        gd_s0 = tdfci.compute_obs(psi, s0_eris);
        print("Site {:.0f} <Sz> (FCI) = {:.6f}".format(the_sites[0],gd_s0)); # site indices, NOT j or d indices
        sdot_eris = tddmrg.get_sz(len(eris_or_driver.h1e[0]), eris_or_driver, the_sites[1], block);
        gd_sdot = tdfci.compute_obs(psi, sdot_eris);
        print("Site {:.0f} <Sz> (FCI) = {:.6f}".format(the_sites[1],gd_sdot));       
        # concurrence between
        C_ci = tddmrg.concurrence_wrapper(psi, eris_or_driver, the_sites, False);
        print("C"+str(the_sites)+" = ",C_ci);
    else:
        # check gd state
        check_E_dmrg = tddmrg.compute_obs(psi, none_or_mpo, eris_or_driver);
        print("Total energy (DMRG) = {:.6f}".format(check_E_dmrg));
        # site spins
        s0_mpo = tddmrg.get_sz(eris_or_driver.n_sites*2, eris_or_driver, the_sites[0], block);
        gd_s0_dmrg = tddmrg.compute_obs(psi, s0_mpo, eris_or_driver);
        print("Site {:.0f} <Sz> (DMRG) = {:.6f}".format(the_sites[0],gd_s0_dmrg));
        sdot_mpo = tddmrg.get_sz(eris_or_driver.n_sites*2, eris_or_driver, the_sites[1], block);
        gd_sdot_dmrg = tddmrg.compute_obs(psi, sdot_mpo, eris_or_driver);
        print("Site {:.0f} <Sz> (DMRG) = {:.6f}".format(the_sites[1], gd_sdot_dmrg));
        # concurrence between 
        C_dmrg = tddmrg.concurrence_wrapper(psi, eris_or_driver, the_sites, True);
        print("C"+str(the_sites)+" = ",C_dmrg);

def check_ham(H):
    size=len(np.shape(H));
    ndofs=np.shape(H)[0];
    if(size==2): # 1 body ham
        for crei in range(ndofs):
            for dei in range(ndofs):
                elem = H[crei,dei];
                deltasz=0;
                modify_deltasz = [1,-1];
                deltasz += modify_deltasz[crei%2];
                deltasz += -modify_deltasz[dei%2];
                if( abs(elem)>1e-12 and deltasz!=0): # nonzero spin flip
                    print("WARNING: nonzero h1e"+str([crei,dei])+" = "+str(elem));
    elif(size==4): # 2 body ham
        for crei in range(ndofs):
            for dei in range(ndofs):
                for crej in range(ndofs):
                    for dej in range(ndofs):
                        elem = H[crei,dei,crej,dej];
                        deltasz = 0;
                        modify_deltasz = [1,-1];
                        deltasz += modify_deltasz[crei%2];
                        deltasz += modify_deltasz[crej%2];
                        deltasz += -modify_deltasz[dei%2];
                        deltasz += -modify_deltasz[dej%2];
                        if( abs(elem)>1e-12 and deltasz!=0): # nonzero spin flip
                            print("WARNING: nonzero h2e"+str([crei,dei,crej,dej])+str(elem));
##################################################################################
#### run code

# top level
verbose = 2; assert verbose in [1,2,3];
np.set_printoptions(precision = 4, suppress = True);
json_name = sys.argv[1];
params = json.load(open(json_name)); print(">>> Params = ",params);
do_fci = bool(int(sys.argv[2]));
do_dmrg = bool(int(sys.argv[3]));
assert(do_fci or do_dmrg);
print(">>> Do FCI  = ",do_fci);
print(">>> Do DMRG = ",do_dmrg);
from transport import tdfci, tddmrg
from transport.tdfci import utils, plot
block_from_fci = False;

# some unpacking
myNL, myNFM, myNR, myNe = params["NL"], params["NFM"], params["NR"], params["Ne"],
mynelec = (myNFM+myNe,0);
my_sites = params["ex_sites"]; # site indices, NOT j or d indices

#### Initialization
####
####
init_start = time.time();

if(do_dmrg): # dmrg gd state
    
    # init ExprBuilder object with terms that are there for all times
    H_driver, H_builder = tddmrg.Hsuper_builder(params, True, scratch_dir=json_name, verbose=verbose); # returns DMRGDriver, ExprBuilder

    # add in t<0 terms
    H_driver, H_mpo_initial = tddmrg.Hsuper_polarizer(params, True, (H_driver,H_builder), verbose=verbose);
    if(block_from_fci):
        H_mpo_initial = H_driver.get_qc_mpo(h1e=H_1e, g2e=H_2e, ecore=0, iprint=5);
        print(H_driver.bw)
        print(H_driver.bw.bs)
        print(type(H_driver.bw.bs.GeneralMPO()))
        print(np.shape(H_1e));
        print(type(H_mpo))
        print(vars(H_mpo))
        assert False
        
    # gd state
    gdstate_mps_inst = H_driver.get_random_mps(tag="gdstate",nroots=1,
                             bond_dim=params["bdim_0"][0] )
    gdstate_E_dmrg = H_driver.dmrg(H_mpo_initial, gdstate_mps_inst,#tol=1e-24, # <------ !!!!!!
        bond_dims=params["bdim_0"], noises=params["noises"], n_sweeps=params["dmrg_sweeps"], cutoff=params["cutoff"],
        iprint=2); # set to 2 to see Mmps
    print("Ground state energy (DMRG) = {:.6f}".format(gdstate_E_dmrg));

    # orbital interactions and reordering
    if False: 
        # have to change sym type to core.SymmetryTypes.SZ in driver constructor
        int_matrix = H_driver.get_orbital_interaction_matrix(gdstate_mps_inst);
        fig, ax = plt.subplots()
        ax.matshow(int_matrix, cmap='ocean_r')
        plt.show()
        assert False

else:
    H_driver, gdstate_mps_inst = None, None;

init_end = time.time();
print(">>> Init compute time (FCI = "+str(do_fci)+", DMRG="+str(do_dmrg)+") = "+str(init_end-init_start));
raise Exception("Stop here!")

#### Observables
####
####
mytime=0;

# plot observables
if(do_fci): check_observables(my_sites, gdstate_ci_inst, H_eris, None, False,mytime);
if(do_dmrg): check_observables(my_sites, gdstate_mps_inst, H_driver, H_mpo_initial, True,mytime);
plot.snapshot_bench(gdstate_ci_inst, gdstate_mps_inst, H_eris, H_driver,
        params, json_name, time = mytime, plot_fig=params["plot"]);

#### Time evolution
####
####
evol1_start = time.time();
time_step = params["time_step"];
time_update = params["t1"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;
        
if(do_fci): # FCI dynamics 
    H_1e_dyn, H_2e_dyn = tddmrg.Hsys_builder(params, False, verbose=verbose);
    print("H_1e_dyn = ");print(H_1e_dyn[:4*myNL,:4*myNL]);print(H_1e_dyn[4*myNL:4*(myNL+myNFM),4*myNL:4*(myNL+myNFM)]);print(H_1e_dyn[4*(myNL+myNFM):,4*(myNL+myNFM):]); 
    #assert False # stop here while constructing zigzag
    H_eris_dyn = tdfci.ERIs(H_1e_dyn, H_2e_dyn, gdstate_scf_inst.mo_coeff);
    t1_ci_inst = tdfci.kernel(gdstate_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t1_ci_inst, H_eris_dyn = None, None;
    
if(do_dmrg): # DMRG dynamics
    H_driver_dyn, H_builder_dyn = tddmrg.Hsys_builder(params, True, scratch_dir = json_name, verbose=verbose);
    H_mpo_dyn = H_driver_dyn.get_mpo(H_builder_dyn.finalize(), iprint=verbose);
    if(block_from_fci):
        H_mpo_dyn = H_driver.get_qc_mpo(h1e=H_1e_dyn, g2e=H_2e_dyn, ecore=0, iprint=5);
        assert False
    t1_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, gdstate_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                    bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=2) # set to two for MMps verbose-1);
    print("\n\n\n**********************\nTime dep mmps should be just above this\n**********************\n\n\n**********************\n\n\n***************************\n\n\n")

else:
    t1_mps_inst, H_driver_dyn = None, None;

evol1_end = time.time();
print(">>> Evol1 compute time (FCI = "+str(do_fci)+", DMRG="+str(do_dmrg)+") = "+str(evol1_end-evol1_start));

# observables
if(do_fci): check_observables(my_sites, t1_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t1_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t1_ci_inst, t1_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);

# time evol 2nd time
evol2_start = time.time();
time_update = params["t2"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;

if(do_dmrg): # DMRG dynamics
    t2_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, t1_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=0);
else:
    t2_mps_inst = None;
    
if(do_fci): # FCI dynamics
    t2_ci_inst = tdfci.kernel(t1_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t2_ci_inst = None;

evol2_end = time.time();
print(">>> Evol2 compute time (FCI = "+str(do_fci)+", DMRG="+str(do_dmrg)+") = "+str(evol2_end-evol2_start));

# observables
if(do_fci): check_observables(my_sites, t2_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t2_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t2_ci_inst, t2_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);

# time evol 3rd time
evol3_start = time.time();
time_update = params["t3"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;

if(do_dmrg): # DMRG dynamics
    t3_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, t2_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=0);
else:
    t3_mps_inst = None;
    
if(do_fci): # FCI dynamics
    t3_ci_inst = tdfci.kernel(t2_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t3_ci_inst = None;
    
evol3_end = time.time();
print(">>> Evol3 compute time (FCI = "+str(do_fci)+", DMRG="+str(do_dmrg)+") = "+str(evol3_end-evol3_start));

# observables
if(do_fci): check_observables(my_sites, t3_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t3_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t3_ci_inst, t3_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);

# time evol 4th time
time_update = params["t4"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;

if(do_dmrg): # DMRG dynamics
    t4_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, t3_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=0);
else:
    t4_mps_inst = None;
    
if(do_fci): # FCI dynamics
    t4_ci_inst = tdfci.kernel(t3_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t4_ci_inst = None;
    
# observables
if(do_fci): check_observables(my_sites, t4_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t4_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t4_ci_inst, t4_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);

# time evol 5th time
time_update = params["t5"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;

if(do_dmrg): # DMRG dynamics
    t5_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, t4_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=0);
else:
    t5_mps_inst = None;
    
if(do_fci): # FCI dynamics
    t5_ci_inst = tdfci.kernel(t4_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t5_ci_inst = None;
    
# observables
if(do_fci): check_observables(my_sites, t5_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t5_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t5_ci_inst, t5_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);

# time evol 6th time
time_update = params["t6"];
time_update = time_step*int(abs(time_update/time_step) + 0.1); # round to discrete # time steps
mytime += time_update;

if(do_dmrg): # DMRG dynamics
    t6_mps_inst = H_driver_dyn.td_dmrg(H_mpo_dyn, t5_mps_inst, delta_t=complex(0,time_step), target_t=complex(0,time_update),
                bond_dims=params["bdim_t"], cutoff=params["cutoff"], te_type=params["te_type"], iprint=0);
else:
    t6_mps_inst = None;
    
if(do_fci): # FCI dynamics
    t6_ci_inst = tdfci.kernel(t5_ci_inst, H_eris_dyn, time_update, time_step);
else:
    t6_ci_inst = None;
    
# observables
if(do_fci): check_observables(my_sites, t6_ci_inst, H_eris_dyn, None, False,mytime);
if(do_dmrg): check_observables(my_sites, t6_mps_inst, H_driver_dyn, H_mpo_dyn, True,mytime);
plot.snapshot_bench(t6_ci_inst, t6_mps_inst, H_eris_dyn, H_driver_dyn,
                    params, json_name, time=mytime, plot_fig=params["plot"]);








