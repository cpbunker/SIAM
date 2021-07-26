'''
Christian Bunker
M^2QM at UF
July 2021

Runner file for benchmarking td-FCI
'''

import ruojings_td_fci
import siam_current
import plot

import numpy as np
import matplotlib.pyplot as plt

if False:

    psi_i = np.array([0,0,0,1,0,0,0,0,0]); # initial wf, eq eigenstate
    psi_c = []; # initial wf in coefs of noneq eigenstates
    t = 1.0; # dot lead hopping
    V = 0.0 # gate voltage
    b = -0.005; # bias
    U = 0.0 # hubbard
    h = np.array([[V,0,0,0,0,t,0,-t,0],
                  [0,V,0,0,t,-t,-t,t,0],
                  [0,0,V,0,-t,0,t,0,0],
                  [0,0,0,V+b,-t,-t,0,0,0],
                  [0,t,-t,-t,b/2,0,0,0,0],
                  [t,-t,0,-t,0,U+2*V+b/2,0,0,0],
                  [0,-t,t,0,0,0,U+2*V-b/2,0,-t],
                  [-t,t,0,0,0,0,0,-b/2,-t],
                  [0,0,0,0,0,0,-t,-t,V-b]]);
    print(h);
    evals, evecs = np.linalg.eigh(h);
    print("0. Exact diagonalization")
    for ei in range(len(evals)):
        psi_c.append(np.dot(psi_i, evecs[ei]) );
        print("- energy = ","{0:.6f}".format(evals[ei]),", coef = ","{0:.6f}".format(psi_c[ei]));
    

##################################################################################
#### replicate results from ruojing's code with siam_current module (ASU formalism)
#### 1_1_0 system to match analytical results

if True:
    verbose = 4;
    nleads = (1,0);
    nelecs = (1,1); # half filling
    nelecs_ASU = (sum(nelecs),0); # all spin up formalism
    splots = ['Jtot','occ']; # which subplots to make

    #time info
    dt = 0.01;
    tf = 5.0;

    # benchmark with spin free code
    params = 1.0, 1.0, -0.005, 0.0, 0.0; # featureless dot
    fname = ruojings_td_fci.SpinfreeTest(nleads, nelecs, tf, dt, phys_params = params, verbose = verbose);
    plot.PlotObservables(nleads, params[1], fname, splots = splots);

    # test ASU code
    params_ASU = 1.0, 1.0, -0.005, 0.0, 0.0, 0.0, 0.0, 0.0; # featureless dot
    fname_ASU = siam_current.DotData(nleads, nelecs_ASU, tf, dt, phys_params=params_ASU, verbose = verbose);
    plot.PlotObservables(nleads, params_ASU[1], fname_ASU);

##################################################################################
#### 3_1_2 system is where both methods should always match

if False:
    verbose = 4;
    nleads = (3,2);
    nelecs = (3,3); # half filling
    nelecs_ASU = (sum(nelecs),0); # all spin up formalism
    splots = ['Jtot','occ','delta_occ','Sz']; # which subplots to make

    #time info
    dt = 0.01;
    tf = 8.0;

    # benchmark with spin free code
    #params = 1.0, 1.0, -0.005, 0.0, 0.0; # featureless dot
    #fname = ruojings_td_fci.SpinfreeTest(nleads, nelecs, tf, dt, phys_params = None, verbose = verbose);
    fname = "dat/SpinfreeTest/312_e6.npy"
    plot.PlotObservables(nleads, 0.4, fname, splots = splots);

    # test ASU code
    #params_ASU = 1.0, 1.0, -0.005, 0.0, 0.0, 0.0, 0.0, 0.0; # featureless dot
    #fname_ASU = siam_current.DotData(nleads, nelecs_ASU, tf, dt, phys_params=None, verbose = verbose);
    fname_ASU = "dat/DotData/3_1_2_e6_B0.0_t0.0_Vg-0.5.npy"
    plot.PlotObservables(nleads, 0.4, fname_ASU, splots = splots);






