'''
Christian Bunker
M^2QM at UF
October 2021

Quasi 1 body transmission through spin impurities project, part 3:
Single electron incident on two identical spin 1 impurities, following Eric's paper
NB impurities have more complicated dynamics than in cicc case:
- on site spin anisotropy
- isotropic exchange interaction between them

wfm.py
- Green's function solution to transmission of incident plane wave
- left leads, right leads infinite chain of hopping tl treated with self energy
- in the middle is a scattering region, hop on/off with th 
- in SR the spin degrees of freedom of the incoming electron and spin impurities are coupled 
'''

from transport import wfm, fci_mod, ops
from transport.wfm import utils

import numpy as np
import matplotlib.pyplot as plt
import itertools

# top level
plt.style.use("seaborn-dark-palette");
np.set_printoptions(precision = 4, suppress = True);
verbose = 3;

# def particles and their single particle states
species = np.array([1,1,1]); # num of each species, which are one e, elec, spin-3/2, spin-3/2
spec_strs = ["e","1","2"];
states = [[0,1],[2,3,4],[5,6,7]]; # e up, down, spin 1 mz, spin 2 mz
state_strs = ["0.5_","-0.5_","1.0_","0.0_","-1.0_","1.0_","0.0_","-1.0_"];
dets = np.array([xi for xi in itertools.product(*tuple(states))]); # product states
dets32 = [[0,2,6],[0,3,5],[1,2,5]]; # total spin 3/2 subspace

# source
sourcei = 2; #| down, 1, 1 > = [1 2 5]
source = np.zeros(len(dets32));
source[sourcei] = 1;
source_str = "|";
for si in dets32[sourcei]: source_str += state_strs[si];
source_str += ">";
print("\nSource:\n"+source_str);

# entangled pair
pair = (0,1); #|up, 1, 0> = [0 2 6] and |up,0,1> = [0,3,5]
if(verbose):
    print("\nEntangled pair:");
    pair_strs = [];
    for pi in pair:
        pair_str = "|";
        for si in dets32[pi]: pair_str += state_strs[si];
        pair_str += ">";
        print(pair_str);
        pair_strs.append(pair_str);

# phys params
tl = 1.0; # hopping >> other params
th = 1.0;
td = 1.0;

# iter over params
#params0 = 1,1,-1,-1; # th, td, eps1, eps2
#for params in wfm.utils.sweep_param_space(params0, 1.0, 7):
for D1 in [0.1,0.2,0.5,1.0,1.5,2.0]:
    D2 = D1;

    # iter over Kondo strength
    for JK1 in [2*D1/3]:
        JK2 = JK1;

        # check lead eigenstates
        h1e_JK0, g2e_JK0 = wfm.utils.h_switzer(D1, D2, 0, 0, 0);
        hSR_JK0 = fci_mod.single_to_det(h1e_JK0, g2e_JK0, species, states, dets_interest=dets32);
        hSR_JK0 = wfm.utils.entangle(hSR_JK0, *pair);
        if(verbose): print("JK1 = JK2 = 0 hamiltonian\n",hSR_JK0);

        # physics of scattering region -> array of [H at octo, H at tetra]
        hblocks, tblocks = [], []; # on site and hopping blocks in the SR
        for impi in range(2):
            if impi == 0: # on imp 1
                h1e, g2e = wfm.utils.h_switzer(D1, D2, 0, JK1, 0);
            else:
                h1e, g2e = wfm.utils.h_switzer(D1, D2, 0, 0, JK2);

            # convert to many body form
            h = fci_mod.single_to_det(h1e,g2e, species, states, dets_interest=dets32);

            # entangle the me up states into eric's me, s12, m12> = up, 2, 1> state
            h = wfm.utils.entangle(h, *pair);
            if(verbose>3): print("\nEntangled hamiltonian\n", h);

            # add to list
            if(impi == 0):
                hblocks.append(np.copy(hSR_JK0)); # LL eigenstates
                tblocks.append(-th*np.eye(np.shape(h)[0])); # hop onto imp 1
                tblocks.append(-td*np.eye(np.shape(h)[0])); # hop onto imp 2
            hblocks.append(h);
        del h, impi, h1e, g2e;

        # finish list
        tblocks.append(-td*np.eye(np.shape(hSR_JK0)[0])); # hop onto RL
        hblocks.append(np.copy(hSR_JK0)); # RL eigenstates
        hblocks = np.array(hblocks);
        tblocks = np.array(tblocks);
        for blocki in range(len(hblocks)): # set mu_LL = 0
            hblocks[blocki] -= hSR_JK0[sourcei,sourcei]*np.eye(np.shape(hblocks[blocki])[0])
        if verbose: print("\nhblocks:\n", hblocks, "\ntblocks:\n", tblocks); 

        # iter over E
        Elims = (-2)*tl, (-1.7)*tl;
        Evals = np.linspace(*Elims, 40);
        Tvals = [];
        for Energy in Evals:
            Tvals.append(wfm.kernel(hblocks, tblocks, tl, Energy, source));
        Tvals = np.array(Tvals); 

        # plot
        fig, ax = plt.subplots();
        ax.scatter(Evals+2*tl, Tvals[:,sourcei], marker = 's', label = "$|i\,>$");
        ax.scatter(Evals+2*tl, Tvals[:,pair[0]], marker = 's', label = "$|+>$");
        ax.scatter(Evals+2*tl, Tvals[:,pair[1]], marker = 's', label = "$|->$");

        # format
        #ax.set_title("Transmission at resonance, $J_K = 2D/3$");
        ax.set_ylabel("$T$");
        ax.set_xlabel("$E + 2t_l$");
        ax.set_ylim(0.0,1.05);
        plt.legend();
        ax.minorticks_on();
        ax.grid(which='major', color='#DDDDDD', linewidth=0.8);
        ax.grid(which='minor', color='#EEEEEE', linestyle=':', linewidth=0.5);
        plt.show();






