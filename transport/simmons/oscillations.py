'''
Simmons formula description of tunneling through a tunnel junction,
under different physical scenarios
'''

from utils import plot_fit, load_dIdV

import numpy as np
import matplotlib.pyplot as plt

# fig standardizing
myxvals = 199;
myfontsize = 14;
mycolors = ["cornflowerblue", "darkgreen", "darkred", "darkcyan", "darkmagenta","darkgray"];
accentcolors = ["black","red"];
mymarkers = ["o","+","^","s","d","*","X"];
mymarkevery = (40, 40);
mylinewidth = 1.0;
mypanels = ["(a)","(b)","(c)","(d)"];
#plt.rcParams.update({"text.usetex": True,"font.family": "Times"});

kelvin2eV =  8.617e-5;
conductance_quantum = 7.748e-5; # units amp/volt

###############################################################
#### fitting dI/dV with background and oscillations

def dIdV_mag(Vb, V0, E0, G1, G0):
    '''
    Surface magnon scattering
    Designed to be passed to scipy.optimize.curve_fit
    '''

    def Gmag(E, kBT):
        # Eq 12 in XGZ's magnon paper
        ret = np.zeros_like(E);
        ret += -2*kBT*np.log(1-np.exp(-E0/kBT));
        ret += (E+E0)/( np.exp( (E+E0)/kBT) - 1);
        ret += (E-E0)/(-np.exp(-(E-E0)/kBT) + 1);
        return ret
        
    return G0+G1*Gmag(abs(Vb-V0), kelvin2eV*temp_kwarg);

def dIdV_imp(Vb, V0, E0, G3, G2):
    '''
    Magnetic impurity scattering
    Designed to be passed to scipy.optimize.curve_fit
    '''

    def Ffunc(E, kBT):
        # Eq 17 in XGZ's magnon paper
        numerator = np.log(1+ E0/(E+kBT));
        denominator = 1 - kBT/(E0+0.4*E) + 12*np.power(kBT/(E0+2.4*E),2);
        return numerator/denominator;

    return G2 - G3*Ffunc(abs(Vb-V0), kelvin2eV*temp_kwarg)


def dIdV_back(Vb, V0, Ec, E0, G1, G2, G3, which='both'):
    '''
    Background, combining surface magnon and impurity effects
    Designed to be passed to scipy.optimize.curve_fit
    Does not combine, instead returns only one if which==imp or mag
    '''

    # get magnon and impurity contributions
    # NB since both contain a background term, I combine these into G2
    # and pass G2/2 to both
    mag_part = dIdV_mag(Vb, V0, Ec, G1, G2/2);
    imp_part = dIdV_imp(Vb, V0, E0, G3, G2/2);

    # what to return
    if(which=='mag'): return mag_part;
    elif(which=='imp'): return imp_part;
    elif(which=='both'): return mag_part+imp_part;
    else: raise NotImplementedError;

def dIdV_sin(Vb, alpha, amplitude, period):
    '''
    Sinusoidal fit function - purely mathematical, not physical
    Designed to be passed to scipy.optimize.curve_fit
    '''

    ang_freq = 2*np.pi/period
    return amplitude*np.sin(ang_freq*Vb-alpha);

def dIdV_lorentz_zero(Vb, V0, dI0, Gamma, EC): 
    '''
    '''
    from landauer import dI_of_Vb_zero

    nmax = 40;
    ns = np.arange(-nmax, nmax+1);
    mymu0 = 0.0; # otherwise breaks equal spacing
    return -dI0+1e9*conductance_quantum*dI_of_Vb_zero(Vb-V0, mymu0, Gamma, EC, 0.0, ns);

def dIdV_lorentz(Vb, V0, dI0, Gamma, EC): 
    '''
    '''
    from landauer import dI_of_Vb

    nmax = 40;
    ns = np.arange(-nmax, nmax+1);
    mymu0 = 0.0; # otherwise breaks equal spacing
    print(">>>", temp_kwarg);
    return -dI0+1e9*conductance_quantum*dI_of_Vb(Vb-V0, mymu0, Gamma, EC, kelvin2eV*temp_kwarg, ns);

####################################################################
#### main

from utils import fit_wrapper

def fit_dIdV(metal, V0_not, dI0_not, Gamma_not, EC_not,
             dI0_percent, Gamma_percent, EC_percent, sine=False, num_sigma = 2, verbose=0):
    '''
    '''

    # load data
    V_exp, dI_exp = load_dIdV("KdIdV.txt",metal, temp_kwarg);
    Vlim = min([abs(np.min(V_exp)), abs(np.max(V_exp))]);   
    dI_sigma= np.std(dI_exp);
    dI_mu = np.mean(dI_exp);
    
    #### fit to background

    # first fit, with outliers present
    Ec_guess, E0_guess = 0.040, 0.040; # tens of meV
    params_back_guess = np.array([0.0, Ec_guess, E0_guess, 3*dI_sigma, dI_mu, 3*dI_sigma]);
    bounds_back = np.array([[-1e-2, Ec_guess*0.5, E0_guess*0.0, 0, 0, 0],
                            [ 1e-2, Ec_guess*2.0, E0_guess*2.0, 5*dI_sigma, 2*dI_mu, 5*dI_sigma]]);
    params_back, _ = fit_wrapper(dIdV_back, V_exp, dI_exp,
                            params_back_guess, bounds_back, ["V0", "Ec", "E0", "G1", "G2", "G3"],
                            stop_bounds = False, verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");

    if True:
        # remove outliers based on background fit
        pre_dropout = len(V_exp);
        background = dIdV_back(V_exp, *params_back);
        V_exp = V_exp[abs(dI_exp-background) < num_sigma*dI_sigma];
        dI_exp = dI_exp[abs(dI_exp-background) < num_sigma*dI_sigma];
        assert(pre_dropout - len(V_exp) <= 5); # only remove a few
        
        # update descriptors
        Vlim = min([abs(np.min(V_exp)), abs(np.max(V_exp))]);   
        dI_sigma= np.std(dI_exp);
        dI_mu = np.mean(dI_exp);

        # second fit, without outliers
        params_back, _ = fit_wrapper(dIdV_back, V_exp, dI_exp,
                                params_back_guess, bounds_back, ["V0", "Ec", "E0", "G1", "G2", "G3"],
                                stop_bounds = True, verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");

        # update and subtract background
        background = dIdV_back(V_exp, *params_back);
        dI_exp = dI_exp - background;
    
    #### fit oscillations

    # fit to sines
    if(sine):
        params_sin_guess = np.array([np.pi/2, dI_sigma, Vlim/5]);
        bounds_sin = [[],[]];
        for pguess in params_sin_guess:
            bounds_sin[0].append(pguess*(1-1));
            bounds_sin[1].append(pguess*(1+1));
        bounds_sin = np.array(bounds_sin);
        (_, amp, per), rmse = fit_wrapper(dIdV_sin, V_exp, dI_exp,
                        params_sin_guess, bounds_sin, ["alpha","amp","per"], verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");
        results = (amp, per, rmse);
        bounds_zero = bounds_sin[:,1:];

    # fit to lorentzians
    else:
        params_zero_guess = np.array([V0_not, dI0_not, Gamma_not, EC_not]);
        bounds_zero = np.array([ [-Vlim/5, dI0_not*(1-dI0_percent), Gamma_not*(1-Gamma_percent), EC_not*(1-EC_percent)],
                   [ Vlim/5, dI0_not*(1+dI0_percent), Gamma_not*(1+Gamma_percent), EC_not*(1+EC_percent) ]]);

        # first fit at T=0
        (V0, dI0, Gamma, EC), rmse = fit_wrapper(dIdV_lorentz_zero, V_exp, dI_exp,
                                 params_zero_guess, bounds_zero, ["V0","dI0","Gamma", "EC"], verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");
        
        # now adjust fit at T != 0
        # only fit dI0 and Gamma in the adjusted fit!!
        params_guess = np.array([V0, dI0, Gamma, EC]);
        bounds = np.array([[V0, dI0*(1-dI0_percent), Gamma*(1-Gamma_percent), EC],
                           [V0+1e-6, dI0*(1+dI0_percent), Gamma*(1+Gamma_percent), EC+1e-6]]);

        import time
        start = time.time()
        (V0, dI0, Gamma, EC), rmse = fit_wrapper(dIdV_lorentz, V_exp, dI_exp,
                                 params_guess, bounds, ["V0","dI0","Gamma", "EC"], verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");
        results = (V0, dI0, Gamma, EC, rmse);
        stop = time.time()
        print("T != 0 fit time = ", stop-start)

    #if(verbose==10): assert False;
    return (results, bounds_zero);

####################################################################
#### wrappers

def fit_Mn_data():
    metal="Mn/"; # points to data folder
    fit_sine = True;

    # experimental params
    kelvin2eV =  8.617e-5;
    Ts = np.array([5.0,10.0,15.0,20.0,25.0,30.0]);

    # guesses
    V0_guess = -0.0044*np.ones_like(Ts);
    dI0_guess = np.array([63063, 65729, 69658, 79283, 77086, 77086]);
    Gamma_guess = 0.0048*np.ones_like(Ts); # gamma dominates T in the smearing
    EC_guess = (0.0196/4)*np.ones_like(Ts);
    dI0_percent = 0.2;
    Gamma_percent = 0.2;
    EC_percent = 0.05;

    #fitting results
    results = [];
    boundsT = [];
    for datai in range(len(Ts)):
        print("#"*60+"\nT = {:.1f} K ({:.4f} eV)".format(Ts[datai], Ts[datai]*kelvin2eV));
        if(fit_sine):
            rlabels = ["Amplitude", "$\Delta V_b$", "RMSE"];
        else:
            rlabels = ["$V_0$", "$dI_0$ (nA/V)", "$\Gamma_0$ (eV)", "$E_C$ (eV)", "RMSE"];

        # get fit results
        global temp_kwarg; temp_kwarg = Ts[datai]; # very bad practice
        temp_results, temp_bounds = fit_dIdV(metal,
            V0_guess[datai], dI0_guess[datai], Gamma_guess[datai], EC_guess[datai],
            dI0_percent, Gamma_percent, EC_percent, verbose=10, sine=fit_sine);
        results.append(temp_results); 
        temp_bounds = np.append(temp_bounds, [[0],[0.1]], axis=1); # fake rmse bounds
        boundsT.append(temp_bounds);

    # plot fitting results vs T
    results, boundsT = np.array(results), np.array(boundsT);
    nresults = len(results[0]);
    fig, axes = plt.subplots(nresults, sharex=True);
    if(nresults==1): axes = [axes];
    for resulti in range(nresults):
        axes[resulti].plot(Ts, results[:,resulti], color=mycolors[0],marker=mymarkers[0]);
        axes[resulti].set_ylabel(rlabels[resulti]);
        if(not fit_sine):
            axes[resulti].plot(Ts,boundsT[:,0,resulti], color=accentcolors[0],linestyle='dashed');
            axes[resulti].plot(Ts,boundsT[:,1,resulti], color=accentcolors[0],linestyle='dashed');
        axes[resulti].ticklabel_format(axis='y',style='sci',scilimits=(0,0));

    # Amp vs T
    if(fit_sine):
        axes[0].plot(Ts, results[0,0]*5/Ts, color = 'red');

    # save
    if False:
        fname = "land_fit/"
        print("Saving data to "+fname);
        np.savetxt(fname+"Ts.txt", Ts);
        np.save(fname+"results.npy", results);
        np.save(fname+"bounds.npy", boundsT);

    # format
    axes[-1].set_xlabel("$T$ (K)");
    plt.show();

def plot_saved_fit():
    '''
    '''
    verbose=1;
    metal="Mn/"; # points to data folder
    kelvin2eV =  8.617e-5;
    radius = 200*1e3; # 200 micro meter
    area = np.pi*radius*radius;

    # load
    fname = "land_fit/"
    print("Loading data from "+fname);
    Ts = np.loadtxt(fname+"Ts.txt");
    Ts = [5,30]
    results = np.load(fname+"results.npy");
    boundsT = np.load(fname+"bounds.npy"); 
    rlabels = ["$V_0$", "$dI_0$ (nA/V)", "$\Gamma_0$ (eV)", "$E_C$ (eV)", "RMSE"];
    
    # plot each fit
    from utils import plot_fit
    for Tvali, Tval in enumerate(Ts):
        if False: # fit already stored
            fname = "land_plots/{:.0f}".format(Tval);
            x = np.load(fname+"_x.npy");
            y = np.load(fname+"_y.npy");
            yfit = np.load(fname+"_yfit.npy");
            try:
                mytxt = open(fname+"_title.txt", "r");
                mytitle = mytxt.readline()[1:];
            finally:
                mytxt.close();
            plot_fit(x, y, yfit, mytitle=mytitle, myylabel="$dI/dV_b$");
        else: # need to generate fit
            V_exp, dI_exp = load_dIdV("KdIdV.txt",metal, Tval);
            Vlim = min([abs(np.min(V_exp)), abs(np.max(V_exp))]);   
            dI_sigma= np.std(dI_exp);
            dI_mu = np.mean(dI_exp);

            # fit to background
            global temp_kwarg; temp_kwarg = Tval; # very bad practice
            params_back_guess = np.array([0.0,Vlim/10, 5*dI_sigma, dI_mu]);
            bounds_back = [ [-1e-2],[1e-2] ];
            for pguess in params_back_guess[1:]:
                bounds_back[0].append(pguess*(1-1));
                bounds_back[1].append(pguess*(1+1));
            bounds_back = np.array(bounds_back);
            params_back, _ = fit_wrapper(dIdV_back, V_exp, dI_exp,
                                    params_back_guess, bounds_back, ["V0", "E0", "G3","G2"], verbose=verbose, myylabel="$dI/dV_b$ (nA/V)");

            # subtract background
            background = dIdV_back(V_exp, *params_back);
            dI_exp = dI_exp - background;

            # fit and plot
            print(*results[Tvali,:-1]);
            assert False
            dI_fit = dIdV_lorentz(V_exp, *results[Tvali,:-1]);
            mytitle="$T = $ {:.1f} K, $\Gamma_0 = $ {:.5f} eV, $E_C = $ {:.5f} eV".format(Tval, *results[Tvali,2:4])
            if(verbose > 4): plot_fit(V_exp, dI_exp, dI_fit, mytitle=mytitle, myylabel="$dI/dV_b$"); 
        
            # save V_exp, dI_exp, dI_fit for easy access
            fname = "land_plots/{:.0f}".format(Tval);
            print("Saving data to "+fname);
            np.save(fname+"_x.npy", V_exp);
            np.save(fname+"_y.npy", dI_exp);
            np.save(fname+"_yfit.npy", dI_fit);
            np.savetxt(fname+"_title.txt", [0], header=mytitle);

    # plot fitting results vs T
    nresults = len(results[0]);
    fig, axes = plt.subplots(nresults, sharex=True);
    if(nresults==1): axes = [axes];
    for resulti in range(nresults):
        axes[resulti].plot(Ts, results[:,resulti], color=mycolors[0],marker=mymarkers[0]);
        axes[resulti].set_ylabel(rlabels[resulti]);
        axes[resulti].plot(Ts,boundsT[:,0,resulti], color=accentcolors[0],linestyle='dashed');
        axes[resulti].plot(Ts,boundsT[:,1,resulti], color=accentcolors[0],linestyle='dashed');
        axes[resulti].ticklabel_format(axis='y',style='sci',scilimits=(0,0));

    # format
    axes[-1].set_xlabel("$T$ (K)");
    plt.show();

####################################################################
#### run

if(__name__ == "__main__"):
    #plot_saved_fit();
    fit_Mn_data();
