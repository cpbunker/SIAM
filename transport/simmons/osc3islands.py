'''
Capacitor model + landauer formula for describing evenly spaced dI/dVb oscillations
due to single electron charging effects
'''

from utils import plot_fit, load_dIdV, fit_wrapper
from landauer import dI_of_Vb, dI_of_Vb_zero

import numpy as np
import matplotlib.pyplot as plt
import random
random.seed(1016)

# fig standardizing
myxvals = 199;
myfontsize = 14;
mycolors = ["cornflowerblue", "darkred", "darkgreen", "darkorange", "darkmagenta","darkgray"];
accentcolors = ["black","red"];
mymarkers = ["o","s","^","d","*","+","X"];
mymarkevery = (40, 40);
mylinewidth = 1.0;
mypanels = ["(a)","(b)","(c)","(d)"];
#plt.rcParams.update({"text.usetex": True,"font.family": "Times"});

# units
kelvin2eV =  8.617e-5;
muBohr = 5.788e-5;     # eV/T
gfactor = 2;

###############################################################
#### fitting dI/dV with background and oscillations

def dIdV_imp(Vb, V0, eps0, G2, G3, T_surf):
    '''
    Magnetic impurity scattering
    Designed to be passed to scipy.optimize.curve_fit
    '''

    def Ffunc(E, kBT):
        # Eq 17 in XGZ's magnon paper
        numerator = np.log(1+ eps0/(E+kBT));
        denominator = 1 - kBT/(eps0+0.4*E) + 12*np.power(kBT/(eps0+2.4*E),2);
        return numerator/denominator;

    # Eq 20 in XGZ's magnon paper
    Delta = muBohr*gfactor*bfield_kwarg;
    retval = G2;
    retval -= (G3/2)*Ffunc(abs(Vb-V0), kelvin2eV*T_surf);
    retval -= (G3/4)*Ffunc(abs(Vb-V0+Delta), kelvin2eV*T_surf);
    retval -= (G3/4)*Ffunc(abs(Vb-V0-Delta), kelvin2eV*T_surf);
    return retval;

def dIdV_mag(Vb, V0, epsc, G1, T_surf):
    '''
    Surface magnon scattering
    Designed to be passed to scipy.optimize.curve_fit
    '''

    def Gmag(E, kBT):
        # Eq 12 in XGZ's magnon paper
        ret = np.zeros_like(E);
        ret += -2*kBT*np.log(1-np.exp(-epsc/kBT));
        ret += (E+epsc)/( np.exp( (E+epsc)/kBT) - 1);
        ret += (E-epsc)/(-np.exp(-(E-epsc)/kBT) + 1);
        return ret;

    # split Vb pos and Vb neg branches
    #Vb_pos, Vb_neg = np.zeros_like(Vb), np.zeros_like(Vb);
    #Vb_pos[Vb>=0] = Vb[Vb>=0];
    #Vb_neg[Vb <0] = Vb[Vb <0];
        
    return G1*Gmag(abs(Vb-V0), kelvin2eV*T_surf);

def dIdV_back(Vb, V0, eps0, epsc, G1, G2, G3, T_surf, Gamma):
    '''
    Magnetic impurity and surface magnon scattering, combined
    Designed to be passed to scipy.optimize.curve_fit
    '''

    # include G dependence on Gamma
    G1, G2, G3 = Gamma*Gamma*G1*1e9, Gamma*Gamma*G2*1e9, Gamma*Gamma*G3*1e9;
    return dIdV_imp(Vb, V0, eps0, G2, G3, T_surf)+dIdV_mag(Vb, V0, epsc, G1, T_surf);

from utils import error_func, comp_with_null

def make_EC_list(EC, delta):
    '''
    '''
    assert(num_EC_kwarg==3);
    return np.array([EC, EC*(1-delta), EC*(1-2*delta)]);

def make_EC_dist(EC_mu):
    '''
    '''
    assert(num_EC_kwarg==3);
    ECs = [];
    for _ in range(num_EC_kwarg):
        ECs.append( EC_mu*random.lognormvariate(0.1, 0.4) );
    return np.array(ECs);

def dIdV_lorentz_zero(Vb, V0, tau0, Gamma, EC, delta): 
    '''
    '''

    nmax = 100; # <- has to be increased with increasing Gamma
    ns = np.arange(-nmax, nmax+1);
    mymu0 = 0.0; # grounded
    ret = np.zeros_like(Vb);
    for ECval in make_EC_list(EC, delta):
        ret += tau0*dI_of_Vb_zero(Vb-V0, mymu0, Gamma, ECval, 0.0, ns);
    return ret;

def dIdV_lorentz_fine(Vb, V0, EC1, EC2, EC3):
    '''
    Like dIdV_lorentz_zero, but doesn't fit tau0 or Gamma, so faster
    '''
    assert(num_EC_kwarg==3);
    
    nmax = 100; # <- has to be increased with increasing Gamma
    ns = np.arange(-nmax, nmax+1);
    mymu0 = 0.0; # grounded
    ret = np.zeros_like(Vb);
    for ECval in [EC1, EC2, EC3]:
        ret += tau0_kwarg*dI_of_Vb_zero(Vb-V0, mymu0, Gamma_kwarg, ECval, 0.0, ns);
    return ret;

def dIdV_all_zero(Vb, V0, eps0, epsc, G1, G2, G3, T_surf, tau0, Gamma, EC, delta):
    '''
    Magnetic impurity surface magnon scattering, and T=0 lorentzian all together
    Designed to be passed to scipy.optimize.curve_fit
    '''

    return dIdV_back(Vb, V0, eps0, epsc, G1, G2, G3, T_surf, Gamma) + dIdV_lorentz_zero(Vb, V0, tau0, Gamma, EC, delta);

def dIdV_all_fine(Vb, V0, eps0, epsc, G1, G2, G3, EC1, EC2, EC3):
    '''
    For refining multiple EC
    '''

    return dIdV_back(Vb, V0, eps0, epsc, G1, G2, G3, temp_kwarg, Gamma_kwarg) + dIdV_lorentz_fine(Vb, V0, EC1, EC2, EC3); 

def search_space_lorentz_zero(V_exp, dI_exp, params_back_guess, bounds_back, lorentz_params, which_error = "rmse", num_trials = 100, verbose=0):
    '''
    '''
    V0, tau0, Gamma, EC_mu, delta = lorentz_params

    # trials
    trial_errors = np.zeros((num_trials,),dtype=float);
    trial_ECs = np.zeros((num_trials, num_EC_kwarg),dtype=float);
    trial_fits = np.zeros((num_trials, len(V_exp)),dtype=float);
    trial_backs = np.zeros((num_trials, len(V_exp)),dtype=float);
    for trial in range(num_trials):

        # oscillation terms on top of background
        dI_osc = np.zeros_like(dI_exp);
        trial_ECs[trial] = make_EC_dist(EC_mu);
        for EC in trial_ECs[trial]:
            dI_osc += dIdV_lorentz_zero(V_exp, V0, tau0, Gamma, EC);
        if(trial % (num_trials//10) == 0): print("Trial #",trial, " ECs = ",trial_ECs[trial]);

        # fit the background
        to_fit_back = dI_exp - dI_osc;
        back_params, _ = fit_wrapper(dIdV_back, V_exp, to_fit_back,
                            params_back_guess, bounds_back, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "T_surf", "Gamma"],
                            stop_bounds = False, verbose=0);
        
        # get fit and cost function
        dI_fit = dI_osc + dIdV_back(V_exp, *back_params);
        trial_errors[trial] = error_func(dI_exp, dI_fit, which=which_error);
        trial_fits[trial] = dI_fit;
        trial_backs[trial] = dIdV_back(V_exp, *back_params);

    # compare across trials
    besti = np.argmin(trial_errors);
    return trial_errors[besti], trial_fits[besti], trial_backs[besti], np.array([V0, tau0, Gamma, *trial_ECs[besti]]);

def dIdV_lorentz_trial(Vb, V0, tau0, Gamma, EC1, EC2, EC3):
    dI_osc = np.zeros_like(Vb);
    for EC in [EC1, EC2, EC3]:
        dI_osc += dIdV_lorentz_zero(Vb, V0, tau0, Gamma, EC);
    return dI_osc;

####################################################################
#### main

def fit_dIdV(metal, nots, percents, stop_at, num_dev=3, verbose=0):
    '''
    The main function for fitting the metal Pc dI/dV data
    The data is stored as metal/__dIdV.txt where __ is the temperature
    Args:
    - metal, str, the name of the metal, also gives path to data folder
    - nots, a tuple of initial guesses for all params:
            - ["V0", "eps0", "epsc", "G1", "G2", "G3", "T_surf"] for impurity & magnon background
            - those, plus dI0, Gamma0, EC, T_film for oscillations
    - percents: tuple of one percent for each entry in not. These are used to
        construct the upper bound =not*(1+percent) and lower bound=not*(1-percent)
    - num_dev, int, how many standard deviations away from initial fit to keep before
            discarding outliers
    '''

    # load data
    V_exp, dI_exp = load_dIdV("KdIdV.txt",metal+"data/", temp_kwarg);
    Vlim = min([abs(np.min(V_exp)), abs(np.max(V_exp))]);
    dI_dev = np.sqrt( np.median(np.power(dI_exp-np.mean(dI_exp),2)));

    # unpack
    V0index = np.argmin( abs(V_exp));
    V0_bound = abs(V_exp[V0index] - V_exp[3+V0index]);
    V0_not, eps0_not, epsc_not, G1_not, G2_not, G3_not, ohm_not, tau0_not, Gamma_not, EC_not, delta_not = nots;
    V0_percent, eps0_percent, epsc_percent, G1_percent, G2_percent, G3_percent, ohm_percent, tau0_percent, Gamma_percent, EC_percent, delta_percent = percents
    params_base = np.array([V0_not, eps0_not, epsc_not, G1_not, G2_not, G3_not, temp_kwarg+ohm_not, tau0_not, Gamma_not, EC_not, delta_not]);
    bounds_base = np.array([[V0_not-V0_bound, eps0_not*(1-eps0_percent), epsc_not*(1-epsc_percent), G1_not*(1-G1_percent), G2_not*(1-G2_percent), G3_not*(1-G3_percent), temp_kwarg+ohm_not*(1-ohm_percent), tau0_not*(1-tau0_percent), Gamma_not*(1-Gamma_percent), EC_not*(1-EC_percent), delta_not*(1-delta_percent)],
                            [V0_not+V0_bound, eps0_not*(1+eps0_percent), epsc_not*(1+epsc_percent), G1_not*(1+G1_percent), G2_not*(1+G2_percent), G3_not*(1+G3_percent), temp_kwarg+ohm_not*(1+ohm_percent), tau0_not*(1+tau0_percent), Gamma_not*(1+Gamma_percent), EC_not*(1+EC_percent), delta_not*(1+delta_percent)]]);

    #### initial fit ####
    # all data present
    # lorentzians turned off
    # Gamma frozen
    back_mask = np.array([1,1,1,1,1,1,1,0,1,0,0]); # turn off lorentzian
    params_init_guess = np.copy(params_base)[back_mask>0];
    bounds_init = np.copy(bounds_base)[:,back_mask>0];
    bounds_init[0,-1] = params_init_guess[-1]; # freeze gamma
    bounds_init[1,-1] = params_init_guess[-1]+1e-12;
    params_init, _ = fit_wrapper(dIdV_back, V_exp, dI_exp,
                            params_init_guess, bounds_init, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "T_surf", "Gamma"],
                            stop_bounds = False, verbose=verbose);
    fit_init = dIdV_back(V_exp, *params_init);
    if(verbose > 4): plot_fit(V_exp, dI_exp, fit_init, mytitle="Initial fit (T= {:.1f} K, B = {:.1f} T)".format(temp_kwarg, bfield_kwarg), myylabel="$dI/dV_b$ (nA/V)");

    # remove outliers
    with_outliers = len(V_exp);
    V_exp = V_exp[abs(dI_exp-fit_init) < num_dev*dI_dev];
    dI_exp = dI_exp[abs(dI_exp-fit_init) < num_dev*dI_dev];
    assert(with_outliers - len(V_exp) <= with_outliers*0.05); # remove no more than 5%

    #### Background fit ####
    # outliers removed
    # lorentzians still turned off
    # Gamma still frozen
    V0_bound = V0_percent;  # reset V0 now that outliers are removed
    params_init[0] = V0_not;bounds_init[0,0] = V0_not-V0_bound;bounds_init[1,0] = V0_not+V0_bound;
    params_back, rmse_back = fit_wrapper(dIdV_back, V_exp, dI_exp,
                                params_init, bounds_init, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "T_surf", "Gamma"],
                                stop_bounds = False, verbose=verbose);
    if(verbose > 4): plot_fit(V_exp, dI_exp, dIdV_back(V_exp, *params_back), derivative=False,
                mytitle="Background fit (T= {:.1f} K, B = {:.1f} T)".format(temp_kwarg, bfield_kwarg), myylabel="$dI/dV_b$ (nA/V)");
    if(stop_at=="back/"): return V_exp, dI_exp, params_back, rmse_back;

    #### Lorentz_zero fit ####
    # outliers removed
    # lorentzians turned on
    # Gamma unfrozen
    params_zero_guess = np.copy(params_base);
    params_zero_guess[back_mask>0] = params_back;
    bounds_zero = np.copy(bounds_base);
    bounds_zero[:,0] = bounds_init[:,0]; # update V0 bounds
    params_zero, rmse_zero = fit_wrapper(dIdV_all_zero, V_exp, dI_exp,
                                 params_zero_guess, bounds_zero, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "T_surf", "tau0", "Gamma", "EC", "delta"],
                                 stop_bounds = False, verbose=verbose);
    if(verbose > 4): plot_fit(V_exp, dI_exp, dIdV_all_zero(V_exp, *params_zero), derivative = False,
                              mytitle="Lorentz_zero fit (T= {:.1f} K, B = {:.1f} T, N = {:.0f})".format(temp_kwarg, bfield_kwarg, num_EC_kwarg)+"\nEC = "+str(np.round(make_EC_list(params_zero[-2],params_zero[-1])*1000, decimals=2))+" meV",   
                              myylabel="$dI/dV_b$ (nA/V)");
    # return osc only
    back_mask_zero = np.array([1,1,1,1,1,1,1,0,1,0,0]);
    osc_mask_zero = np.array([1,0,0,0,0,0,0,1,1,1,1]);
    dI_back_zero = dIdV_back(V_exp, *params_zero[back_mask_zero>0]);
    if(stop_at=="lorentz_zero/"): return V_exp, dI_exp-dI_back_zero, params_zero[osc_mask_zero>0], rmse_zero;

    #### fine tune the lorentz_zero fit ####
    # outliers removed
    # lorentzians turned on
    # Gamma frozen
    fine_mask = np.array([1,1,1,1,1,1,0,0,0,0,0]);
    params_fine_guess = params_zero[fine_mask>0];
    EClist = make_EC_list(params_zero[-2], params_zero[-1]);
    params_fine_guess = np.append(params_fine_guess, EClist);
    global Gamma_kwarg; Gamma_kwarg = params_zero[-3];
    global tau0_kwarg; tau0_kwarg = params_zero[-4];
    bounds_fine = bounds_base[:,fine_mask>0];
    bounds_fine[:,0] = bounds_init[:,0]; # update V0 bounds
    bounds_fine = np.append(bounds_fine, np.array([[EClist[0]*(1-EC_percent),EClist[1]*(1-EC_percent),EClist[2]*(1-EC_percent)],
                                                   [EClist[0]*(1+EC_percent),EClist[1]*(1+EC_percent),EClist[2]*(1+EC_percent)]]), axis = 1);
    params_fine, rmse_fine = fit_wrapper(dIdV_all_fine, V_exp, dI_exp,
                                 params_fine_guess, bounds_fine, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "EC1", "EC2", "EC3"],
                                 stop_bounds = False, verbose=verbose);  print("tau0_kwarg = ",tau0_kwarg,"\nGamma_kwarg = ",Gamma_kwarg);
    if(verbose > 4): plot_fit(V_exp, dI_exp, dIdV_all_fine(V_exp, *params_fine), derivative = False,
                              mytitle="Lorentz_fine fit (T= {:.1f} K, B = {:.1f} T, N = {:.0f})".format(temp_kwarg, bfield_kwarg, num_EC_kwarg)+"\nEC = "+str(np.round(params_fine[-num_EC_kwarg:]*1000, decimals=2))+" meV",   
                              myylabel="$dI/dV_b$ (nA/V)");
    
    # return osc only
    osc_mask_fine = np.array([1,0,0,0,0,0,1,1,1]);
    params_fine_back = np.array([params_fine[0], params_fine[1], params_fine[2], params_fine[3], params_fine[4], params_fine[5], temp_kwarg, Gamma_kwarg]);
    dI_back_fine = dIdV_back(V_exp, *params_fine_back);
    if(stop_at=="lorentz_fine/"): return V_exp, dI_exp-dI_back_fine, params_fine[osc_mask_fine>0], rmse_fine;

    #### try a bunch of different combinations ####
    if(stop_at == "trial/"):
        rmse_trial, fit_trial, back_trial, params_trial = search_space_lorentz_zero(V_exp, dI_exp, params_fine_back, bounds_zero[:,back_mask_zero>0],
                            (params_fine[0], tau0_kwarg, Gamma_kwarg, np.average(params_fine[-num_EC_kwarg:])) );
        if(verbose > 4): plot_fit(V_exp, dI_exp, fit_trial, derivative = False,
                                  mytitle="Best fit from search (T= {:.1f} K, B = {:.1f} T, N = {:.0f})".format(temp_kwarg, bfield_kwarg, num_EC_kwarg)+"\nEC = "+str(np.round(params_trial[-num_EC_kwarg:]*1000, decimals=2))+" meV",
                                  myylabel="$dI/dV_b$ (nA/V)");
        if(stop_at=="trial/"): return V_exp, dI_exp-back_trial, params_trial, rmse_trial;

    #### fit a local region only ####
    del params_zero_guess, params_zero, bounds_zero, dI_back_zero, rmse_zero, params_fine_guess, params_fine, bounds_fine, params_fine_back, dI_back_fine, rmse_fine;
    if(temp_kwarg==15.0): V0_not = -0.0028;
    Vmax = 0.015;
    G3_not, tau0_not, EC_not, delta_not = 1e-12, 0.001, 0.00068, 0.01; # just change things by hand here
    EC_d_kwarg = 0.0; # in phase
    dI_exp = dI_exp[V_exp>V0_not];
    V_exp = V_exp[V_exp>V0_not];
    dI_exp = dI_exp[V_exp<Vmax];
    V_exp = V_exp[V_exp<Vmax];
    params_local_guess = np.array([V0_not, eps0_not, epsc_not, G1_not, G2_not, G3_not, temp_kwarg+ohm_not, tau0_not, Gamma_not, EC_not, delta_not]);
    bounds_local = np.array([[V0_not-V0_bound, eps0_not*(1-eps0_percent), epsc_not*(1-epsc_percent), G1_not*(1-G1_percent), G2_not*(1-G2_percent), G3_not*(1-G3_percent), temp_kwarg+ohm_not*(1-ohm_percent), tau0_not*(1-tau0_percent), Gamma_not*(1-Gamma_percent), EC_not*(1-EC_percent), delta_not*(1-delta_percent) ],
                            [V0_not+V0_bound, eps0_not*(1+eps0_percent), epsc_not*(1+epsc_percent), G1_not*(1+G1_percent), G2_not*(1+G2_percent), G3_not*(1+G3_percent), temp_kwarg+ohm_not*(1+ohm_percent), tau0_not*(1+tau0_percent), Gamma_not*(1+Gamma_percent), EC_not*(1+EC_percent), delta_not*(1+delta_percent) ]]);
    params_local, rmse_local = fit_wrapper(dIdV_all_zero, V_exp, dI_exp,
                                 params_local_guess, bounds_local, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "T_surf", "tau0", "Gamma", "EC", "delta"],
                                 stop_bounds = False, verbose=verbose);
    if(verbose > 4): plot_fit(V_exp, dI_exp, dIdV_all_zero(V_exp, *params_local), derivative = False,
                              mytitle="Local fit (T= {:.1f} K, B = {:.1f} T, N = {:.0f})".format(temp_kwarg, bfield_kwarg, num_EC_kwarg)+"\nEC = "+str(np.round(make_EC_list(params_local[-2], params_local[-1])*1000, decimals=2))+" meV",   
                              myylabel="$dI/dV_b$ (nA/V)");

    # return osc only
    back_mask_local = np.array([1,1,1,1,1,1,1,0,1,0,0]);
    osc_mask_local = np.array([1,0,0,0,0,0,0,1,1,1,1]);
    dI_back_local = dIdV_back(V_exp, *params_local[back_mask_local>0]);
    if(stop_at=="local/"): return V_exp, dI_exp-dI_back_local, params_local[osc_mask_local>0], rmse_local;

    #### in above local fit EC1 = EC2 = EC3, now we fine tune this ####
    localfine_mask = np.array([1,1,1,1,1,1,0,0,0,0,0]);
    params_localfine_guess = params_local[localfine_mask>0];
    EClist = make_EC_list(params_local[-2], params_local[-1]);
    params_localfine_guess = np.append(params_localfine_guess, EClist);
    Gamma_kwarg = params_local[-3];
    tau0_kwarg = params_local[-4];
    bounds_localfine = bounds_local[:,localfine_mask>0];
    # update V0 bounds
    bounds_localfine = np.append(bounds_localfine, np.array([[EClist[0]*(1-EC_percent),EClist[1]*(1-EC_percent),EClist[2]*(1-EC_percent)],
                                                   [EClist[0]*(1+EC_percent),EClist[1]*(1+EC_percent),EClist[2]*(1+EC_percent)]]), axis = 1);
    params_localfine, rmse_localfine = fit_wrapper(dIdV_all_fine, V_exp, dI_exp,
                                 params_localfine_guess, bounds_localfine, ["V0", "eps_0", "eps_c", "G1", "G2", "G3", "EC1", "EC2", "EC3"],
                                 stop_bounds = False, verbose=verbose);
    if(verbose > 4): plot_fit(V_exp, dI_exp, dIdV_all_fine(V_exp, *params_localfine), derivative = False,
                              mytitle="Local fine fit (T= {:.1f} K, B = {:.1f} T, N = {:.0f})".format(temp_kwarg, bfield_kwarg, num_EC_kwarg)+"\nEC = "+str(np.round(params_localfine[-num_EC_kwarg:]*1000, decimals=2))+" meV",   
                              myylabel="$dI/dV_b$ (nA/V)");
    
    # return osc only
    osc_mask_localfine = np.array([1,0,0,0,0,0,1,1,1]);
    params_localfine_back = np.array([params_localfine[0], params_localfine[1], params_localfine[2], params_localfine[3], params_localfine[4], params_localfine[5], temp_kwarg, Gamma_kwarg]);
    dI_back_localfine = dIdV_back(V_exp, *params_localfine_back);
    if(stop_at=="localfine/"): return V_exp, dI_exp-dI_back_localfine, params_localfine[osc_mask_localfine>0], rmse_localfine;

 
####################################################################
#### wrappers

def fit_Mn_data(stop_at, metal, num_islands = 3, verbose=1):
    '''
    '''
    stopats_2_func = {"back/" : dIdV_all_zero, "lorentz_zero/" : dIdV_lorentz_zero, "lorentz_fine/" : dIdV_lorentz_fine, "trial/" : dIdV_lorentz_trial,  "local/" : dIdV_lorentz_zero, "localfine/" : dIdV_lorentz_fine};

    # experimental params
    Ts = np.loadtxt(metal+"Ts.txt", ndmin=1);
    Bs = np.loadtxt(metal+"Bs.txt", ndmin=1);
    if(verbose>10):
        from utils import show_raw_data
        show_raw_data(metal, Ts);

    #### guesses ####
    # surface magnons
    epsc_guess, epsc_percent = 0.002, 1;
    G1_guess, G1_percent = 50.0, 0.5;
    Gamma_guess, Gamma_percent = 0.0006, 0.5;
    # magnetic impurities
    eps0_guess, eps0_percent = 0.002, 0.5;
    G2_guess, G2_percent = 1.2, 0.5;
    G3_guess, G3_percent = 0.5, 0.5;
    # other
    ohm_guess, ohm_percent = 1e-12, 1.0;
    tau0_guess, tau0_percent = 0.002, 0.5; 
    EC_guess, EC_percent = 0.0012, 0.5;
    delta_guess, delta_percent = 0.1, 1;
    V0_guesses = np.array([-0.002413,-0.0035,-0.002089,-0.002226,-0.0026048,-0.001825, -0.0013]);
    V0_percent = 1e-12;

    #fitting results
    results = [];
    for datai in range(len(Ts)):
        if(True and Ts[datai] in [3.0,15.0]): 
            global temp_kwarg; temp_kwarg = Ts[datai];
            global bfield_kwarg; bfield_kwarg = Bs[datai];
            global num_EC_kwarg; num_EC_kwarg = num_islands;
            print("#"*60+"\nT = {:.1f} K".format(Ts[datai]));
            
            #### get fit results ####
            guesses = (V0_guesses[datai], eps0_guess, epsc_guess, G1_guess, G2_guess, G3_guess, ohm_guess, tau0_guess, Gamma_guess, EC_guess, delta_guess);
            percents = (V0_percent, eps0_percent, epsc_percent, G1_percent, G2_percent, G3_percent, ohm_percent, tau0_percent, Gamma_percent, EC_percent, delta_percent);    
            x_forfit, y_forfit, temp_results, temp_rmse = fit_dIdV(metal,
                    guesses, percents, stop_at, verbose=verbose);
            results.append(temp_results);            
            if(stop_at in ["lorentz_zero/", "lorentz_fine/", "trial/","local/", "localfine/"]):
                # compare with null
                y_fit = stopats_2_func[stop_at](x_forfit, *temp_results);  

                #save processed x and y data, and store plot
                plot_fname = metal+stop_at+"stored_plots/{:.0f}".format(Ts[datai]); # <- where to save the fit plot
                print("Saving plot to "+plot_fname);
                np.save(plot_fname+"_x.npy", x_forfit);
                np.save(plot_fname+"_y.npy", y_forfit);
                np.save(plot_fname+"_yfit.npy", y_fit);
                header_str =  str(["V0","tau0","Gamma","EC","delta"])+", RMSE = "+str(temp_rmse);
                if "fine" in stop_at: header_str = header_str =  str(["V0","EC1","EC2","EC3"])+", RMSE = "+str(temp_rmse);
                np.savetxt(plot_fname+"_results.txt", temp_results, header = header_str, fmt = "%.5f", delimiter=' & ');

def plot_saved_fit(stop_at, metal, combined=[], offset = 1000, verbose = 1):
    '''
    '''

    # plot each fit
    Ts = np.loadtxt(metal+"Ts.txt", ndmin=1);
    Bs = np.loadtxt(metal+"Bs.txt", ndmin=1);
    fig3, ax3 = plt.subplots();
    for Tvali, Tval in enumerate(Ts):
        if(Tval in [3.0, 15.0]):
            plot_fname = metal+stop_at+"stored_plots/{:.0f}".format(Tval); # <- where to get/save the fit plot
            temp_results = np.loadtxt(plot_fname+"_results.txt");
            x = np.load(plot_fname+"_x.npy");
            y = np.load(plot_fname+"_y.npy");
            yfit = np.load(plot_fname+"_yfit.npy");
            print("Loading fit from "+plot_fname+"_yfit.npy");

            # plot
            if(combined): # plot all at once
                if(Tval in combined):
                    ax3.scatter(x,offset*Tvali+y, color=mycolors[Tvali], marker=mymarkers[Tvali], 
                                label="$T=$ {:.1f} K".format(Tval)+", B = {:.1f} T".format(Bs[Tvali]));
                    ax3.plot(x,offset*Tvali+yfit, color="black");
                    ax3.set_xlabel("$V_b$ (V)");
                    ax3.set_xlim(-0.1,0.1);
                    ax3.set_ylabel("$dI/dV_b$ (nA/V)");
                    #ax3.set_ylim(300,2800);

            else:               
                from utils import plot_fit
                if(verbose): plot_fit(x, y, yfit, myylabel="$dI/dV_b$ (nA/V)", mytitle="$T=$ {:.1f} K".format(Tval)+", B = {:.1f} T".format(Bs[Tvali]));
                comp_with_null(x, y, yfit, verbose=verbose);

    # show
    ax3.set_title("Conductance oscillations in EGaIn$|$H$_2$Pc$|$MnPc$|$H$_2$Pc$|$NCO");
    plt.legend(loc='lower right');
    plt.show();
              

####################################################################
#### run

if(__name__ == "__main__"):

    metal = "MnTrilayer/"; # tells which experimental data to load
    stop_ats = ["back/", "lorentz_zero/", "lorentz_fine/", "local/", "localfine/", "trial/"];
    stop_at = stop_ats[4];
    verbose=1;

    # this one executes the fitting and stores results
    fit_Mn_data(stop_at, metal, verbose=verbose);

    # this one plots the stored results
    # combined allows you to plot two temps side by side
    #plot_saved_fit(stop_at, metal, verbose=verbose, combined=[]);
