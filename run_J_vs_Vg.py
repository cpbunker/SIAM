'''
Christian Bunker
M^2QM at UF
August 2021

Runner file for simulating current through single dot SIAM, weak biasing, using td-fci
Model runner for anything in single dot weak biasing regime
'''

import siam_current

import numpy as np

import sys

##################################################################################
#### 

# top level
verbose = 3;
nleads = (1,1);
nelecs = (3,0); # half filling
ndots = 2;
get_data = int(sys.argv[1]); # whether to run computations, if not data already exists
spinstate = "aaa";

# phys params, must be floats
tl = 1.0;
th = 1.0;
td = 1.0; 
Vb = 0.0;
mu = 0.0;
Vgs = [-5.0, -8.0, -10.0];
U =  0.0;
B = 1000.0;
theta = 0.0;

#time info
dt = 0.01
tf = 150.0;

if get_data: # must actually compute data

    for i in range(len(Vgs)): # iter over Vg vals;
        Vg = Vgs[i];
        params = tl, th, td, Vb, mu, Vg, U, B, theta;
        siam_current.DotData(nleads, nelecs, ndots, tf, dt, params, spinstate = spinstate, prefix = "dat/param_tuning/Vg/", verbose = verbose);

else:

    import plot

    # plot results
    datafs = sys.argv[2:]
    labs = Vgs # one label for each Vg
    splots = ['occRL']; # which subplots to plot
    title = "Itinerant electron and two dots, |"+spinstate+"$\\rangle$";
    for wi in range(len(datafs)):
        plot.CompObservables(datafs, labs, whichi=wi, splots = splots, sites = ['LL','LD','RD','RL'], mytitle = title, leg_title = "$V_g$");

    








