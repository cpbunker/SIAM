'''
Christian Bunker
M^2QM at UF
September 2021

Recreate sequential tunneling (ST) results in Recher's "quantum dot paper as spin filter" paper
Should see large current when energy of singlet state = 2Vg+U \approx mu
'''

import siam_current

import numpy as np

import sys

##################################################################################
#### set up physics of dot

# top level
verbose = 3;
nleads = (4,4);
nelecs = (sum(nleads)+1,0); # half filling
ndots = 1;
get_data = int(sys.argv[1]); # whether to run computations, if not data already exists

# phys params, must be floats
tl = 1.0;
th = 0.1;
td = 0.0;
Vb = 10.0;
mu = 1.0;
Vgs = [-10.0];
U =  20.0;
B = 1.0*tl;
theta = 0.0;

#time info
dt = 0.04;
tf = 1.0;

if get_data: # must actually compute data

    for i in range(len(Vgs)): # iter over Vg vals;
        Vg = Vgs[i];
        params = tl, th, td, Vb, mu, Vg, U, B, theta;
        siam_current.DotData(nleads, nelecs, ndots, tf, dt, params, prefix = "", verbose = verbose);

else:

    import plot

    # plot results
    datafs = sys.argv[2:]
    labs = Vgs # one label for each Vg
    splots = ['Jup','Jdown','delta_occ','Sz','Szleads','E']; # which subplots to plot
    title = "Current between impurity and left, right leads"
    plot.CompObservables(datafs, labs, splots = splots, mytitle = title, leg_title = "$V_g$", leg_ncol = 1, whichi = 0);

    







