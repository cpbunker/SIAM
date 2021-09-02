'''
Christian Bunker
M^2QM at UF
September 2021

Recreate sequential tunneling (ST) results in Recher's "quantum dot paper as spin filter" paper
Should see large current when energy of singlet state ~ mu
'''

import siam_current

import numpy as np

import sys

##################################################################################
#### set up physics of dot

# top level
verbose = 3;
nleads = (6,6);
nelecs = (sum(nleads)+1,0); # half filling
get_data = int(sys.argv[1]); # whether to run computations, if not data already exists

# phys params, must be floats
tl = 1.0;
th = 0.1; # can scale down and same effects are seen. Make sure to do later
Vb = 10.0;
mu = 1.0;
Vgs = [-10.0];
U =  20.0;
B = 0.0*tl;
theta = 0.0;

#time info
dt = 0.04;
tf = 1.0;

# dmrg
bdims = [700, 800, 900, 1000];
noises = [1e-3, 1e-4, 1e-5,1e-6];

if get_data: # must actually compute data

    for i in range(len(Vgs)): # iter over Vg vals;
        Vg = Vgs[i];
        params = tl, th, Vb, mu, Vg, U, B, theta;
        siam_current.DotDataDmrg(nleads, nelecs, tf, dt, params, bdims, noises, prefix = "", verbose = verbose);

else:

    import plot

    # plot results
    datafs = sys.argv[2:]
    labs = Vgs # one label for each Vg
    splots = ['Jup','Jdown','delta_occ','Sz','Szleads','E']; # which subplots to plot
    title = "Current between impurity and left, right leads"
    plot.CompObservables(datafs, labs, splots = splots, mytitle = title, leg_title = "$V_g$", leg_ncol = 1, whichi = 0);

    







