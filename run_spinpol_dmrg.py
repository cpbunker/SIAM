'''
Christian Bunker
M^2QM at UF
July 2021

Runner file for prepping dot spin state with B field
'''

import siam_current
import plot

import time
import numpy as np
import matplotlib.pyplot as plt

##################################################################################
#### prepare dot in diff spin states

# top level
verbose = 4;
nleads = (4,4);
nelecs = (sum(nleads)+1,0); # half filling
get_data = True # whether to run computations, if not data already exists

# phys params, must be floats
tl = 1.0;
th = 0.4;
Vb = -0.005;
mu = 0.0;
Vg = -0.5;
U = 1.0
Bs = [tl*5, tl*5, tl*5,tl*5,tl*5];
thetas = [0.0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi];
Bs = [tl*5]
thetas = [0.0]

#time info
dt = 0.01;
tf = 0.1;

datafs = [];
times = [];
if get_data: # must actually compute data

    for i in range(len(Bs)): # iter over B, theta inputs

        # timing info for dmrg data run
        start_t = time.time();

        # data run at this particular B, theta
        B, theta = Bs[i], thetas[i];
        params = tl, th, Vb, mu, Vg, U, B, theta;
        fname = siam_current.DotDataDmrg(nleads, nelecs, tf, dt, phys_params=params, Rlead_pol = 1, prefix = "spinpol/", verbose = verbose);
        datafs.append(fname);

        # end timing
        stop_t = time.time();
        times.append(stop_t - start_t);

    # print out timing info when done
    print("Timing Info:");
    print(times);
    print("Number of time steps = ",tf/dt);

else: # already there
    splots = ['Jtot','J','Sz','Szleads']; # which subplots to plot
    for i in range(len(Bs)):
        datafs.append("dat/DotDataDmrg/spinpol/"+str(nleads[0])+"_1_"+str(nleads[1])+"_e"+str(sum(nelecs))+"_B"+str(Bs[i])+"_t"+str(thetas[i])[:3]+"_Vg"+str(Vg)+".npy");
        
    plot.CompObservablesB(datafs, nleads, Bs,thetas, Vg, splots = splots);

    








