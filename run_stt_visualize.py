'''
'''
import matplotlib.pyplot as plt
import numpy as np
import matplotlib.animation as animation

import sys
import json

########################################################################
#### functions

def get_fname(the_path, the_obs, the_xy, the_time):
    '''
    '''
    return the_path+"_arrays/"+the_obs+the_xy+"js_time{:.2f}.npy".format(the_time)

def get_ylabel(the_obs, the_factor, dstring="d"):
    '''
    '''
    if(isinstance(dstring, int)): 
        dstringp1 = "{:.0f}".format(dstring+1);
        dstring = "{:.0f}".format(dstring);
    else:
        dstringp1 = dstring+" + 1";
        
    if(the_obs=="Sdz_"): ret = "{:.0f}".format(the_factor)+"$\langle S_"+dstring+"^z \\rangle /\hbar$";
    elif(the_obs=="occ_"): ret = "${:.0f}\langle n_j \\rangle$".format(the_factor);
    elif(the_obs=="sz_"): ret = "${:.0f}\langle s_j^z \\rangle /\hbar$".format(the_factor);
    elif(the_obs=="pur_"): ret = "{:.0f}".format(the_factor)+"$|\mathbf{S}_"+dstring+"|$";
    elif(the_obs== "conc_"): ret = "{:.0f}".format(the_factor)+"$ C_{"+dstring+", "+dstring+"+1}$";
    elif(the_obs=="S2_"): ret = "{:.1f}".format(the_factor)+"$\langle (\mathbf{S}_"+dstring+" + \mathbf{S}_{"+dstringp1+"})^2 \\rangle/\hbar^2$";
    elif(the_obs=="MI_"): ret = "$\\frac{1}{\ln(2)}MI["+dstring+", "+dstringp1+"]$";
    else: print(the_obs); raise NotImplementedError;
    print(the_obs,"-->",ret);
    return ret;

########################################################################
#### run code

# top level
case = int(sys.argv[1]);
update0 = int(sys.argv[2]);  # time to start at, in units of update interval
datafiles = sys.argv[3:];

# plotting
obs1, factor1, color1, mark1, = "Sdz_", 2,"darkred", "s";
ticks1, linewidth1, fontsize1 =  (-1.0,-0.5,0.0,0.5,1.0), 3.0, 16;
obs2, factor2, color2, mark2 = "occ_", 1, "cornflowerblue", "o";
obs3, factor3, color3, mark3 = "sz_", 2, "darkblue", "o";
num_xticks = 4;
datamarkers = ["s","^","d","*"];

if(case in [0]): # standard charge density vs site snapshot
    from transport import tddmrg
    from transport.tddmrg import plot
    datafile = datafiles[0];
    params = json.load(open(datafile+".txt"));
    print("\nUpdate time = {:.2f}".format(params["tupdate"]));
    tddmrg.plot.snapshot_fromdata(datafile, update0*params["tupdate"], "STT")

if(case in [1,2]): # observables vs time
    datafile = datafiles[0];
    params = json.load(open(datafile+".txt"));
    if(case in [2]): plot_S2 = True;
    else: plot_S2 = False; 

    # axes
    fig, ax = plt.subplots();
    for tick in ticks1: ax.axhline(tick,linestyle=(0,(5,5)),color="gray");
    ax.set_yticks(ticks1);
    ax.set_xlabel("Time $(\hbar/t_l)$", fontsize = fontsize1);
    ax.set_title( open(datafile+"_arrays/"+obs2+"title.txt","r").read().splitlines()[0][1:]);

    # time evolution params
    Nupdates, tupdate = params["Nupdates"]-update0, params["tupdate"];
    times = np.zeros((Nupdates+1,),dtype=float);
    print("\nUpdate time = {:.2f}".format(params["tupdate"]));
    for ti in range(len(times)):
        times[ti] = (update0 + ti)*tupdate;

    # impurity spin vs time
    Nsites = params["NL"]+params["NFM"]+params["NR"]; # number of j sites
    which_imp = 0;
    yds_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
    for ti in range(len(times)):
        yds_vs_time[ti] = np.load(datafile+"_arrays/"+obs1+"yjs_time{:.2f}.npy".format(times[ti]));
    ax.plot(times,factor1*yds_vs_time[:,which_imp],color=color1);
    ax.set_ylabel(get_ylabel(obs1, factor1, dstring=which_imp), color=color1, fontsize=fontsize1);

    # AVERAGE electron spin vs time
    Ne = params["Ne"]; # number deloc electrons
    factor3 = factor3/Ne; # sum normalization
    yjs_vs_time = np.zeros((len(times),Nsites),dtype=float);
    for ti in range(len(times)):
        yjs_vs_time[ti] = np.load(datafile+"_arrays/"+obs3+"yjs_time{:.2f}.npy".format(times[ti]));
    yjsum_vs_time = np.sum(yjs_vs_time, axis=1);
    ax.plot(times, factor3*yjsum_vs_time,color=color3);
    ax3 = ax.twinx();
    ax3.yaxis.set_label_position("left");
    ax3.spines.left.set_position(("axes", -0.15));
    ax3.spines.left.set(alpha=0.0);
    ax3.set_yticks([]);
    label3 = "$\\frac{1}{N_e} \sum_j  2\langle s_j^z \\rangle /\hbar $";
    print(obs3,"-->",label3);
    ax3.set_ylabel(label3, color=color3, fontsize=fontsize1);

    if(plot_S2): # plot S^2
        obs4, factor4, color4 = "S2_", 0.5, "black";
        label4 = get_ylabel(obs4, factor4, dstring=which_imp);
        S2_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
        for ti in range(len(times)):
            S2_vs_time[ti] = np.load(datafile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(times[ti]));
        ax.plot(times, factor4*S2_vs_time[:,which_imp],color=color4);
    else: # plot mutual info
        obs4, factor4, color4 = "MI_", 1/np.log(2), "black";
        label4 = get_ylabel(obs4, factor4, dstring=which_imp);
        S2_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
        for ti in range(len(times)):
            S2_vs_time[ti] = np.load(datafile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(times[ti]));
        ax.plot(times, factor4*S2_vs_time[:,which_imp],color=color4);
    ax4 = ax.twinx();
    ax4.yaxis.set_label_position("right");
    ax4.spines.right.set_position(("axes", 1.0));
    ax4.spines.right.set(alpha=1.0);
    ax4.set_yticks([])
    ax4.set_ylabel(label4, color=color4, fontsize=fontsize1);

    # show
    plt.tight_layout();
    plt.show();

if(case in [3,4]): # observables vs time, for two data sets side by side

    # axes
    fig, ax = plt.subplots();
    params = json.load(open(datafiles[0]+".txt"));
    if(case in [4]): plot_S2 = True;
    else: plot_S2 = False;     

    #### iter over triplet/singlet
    for dfile in datafiles:
        if("singlet" in dfile): mylinestyle = "dashed"; ticks1 = (0.0,0.5,1.0);
        elif("triplet" in dfile): mylinestyle = "solid"; ticks1 = (0.0,0.5,1.0);
        else: mylinestyle = "solid"; ticks1 = (-1.0,-0.5,0.0,0.5,1.0);
        print("\n>>>",mylinestyle,"=",dfile);
        
        # time evolution params
        params = json.load(open(dfile+".txt"));
        Nupdates, tupdate = params["Nupdates"]-update0, params["tupdate"];
        print("\nUpdate time = {:.2f}".format(params["tupdate"]));
        times = np.zeros((Nupdates+1,),dtype=float);
        for ti in range(len(times)):
            times[ti] = (update0 + ti)*tupdate;

        # which imps to get data for
        which_imp = 0;
        assert(which_imp == 0);
        assert(params["NFM"] == 2); # number of d sites
        Nsites = params["NL"]+params["NFM"]+params["NR"]; # number of j sites

        # COMBINED impurity z spin vs time
        obs1, factor1, color1 = "Sdz_", 1, "darkred";
        label1 = "$ \langle S_1^z + S_2^z \\rangle /\hbar$";
        print(obs1,"-->",label1);
        yds_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
        for ti in range(len(times)):
            yds_vs_time[ti] = np.load(dfile+"_arrays/"+obs1+"yjs_time{:.2f}.npy".format(times[ti]));
        yds_summed = np.sum(yds_vs_time, axis=1);
        ax.plot(times,yds_summed,color=color1, linestyle=mylinestyle);
        ax.set_ylabel(label1, color=color1, fontsize=fontsize1);

        # COMBINED electron spin vs time
        Ne = params["Ne"]; # number deloc electrons
        factor3 = 2/Ne; # sum normalization
        label3 = "$\\frac{1}{N_e} \sum_j  2\langle s_j^z \\rangle /\hbar $";
        print(obs3,"-->",label3);
        yjs_vs_time = np.zeros((len(times),Nsites),dtype=float);
        for ti in range(len(times)):
            yjs_vs_time[ti] = np.load(dfile+"_arrays/"+obs3+"yjs_time{:.2f}.npy".format(times[ti]));
        yjs_summed = np.sum(yjs_vs_time, axis=1);
        ax.plot(times, factor3*yjs_summed,color=color3, linestyle=mylinestyle);
    
        # (S1 + S2)^2
        if(plot_S2):
            obs4, factor4, color4 = "S2_", 0.5, "black";
            label4 = get_ylabel(obs4, factor4, dstring=which_imp);
            S2_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
            for ti in range(len(times)):
                S2_vs_time[ti] = np.load(dfile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(times[ti]));
            ax.plot(times, factor4*S2_vs_time[:,which_imp],color=color4, linestyle=mylinestyle);
        else: # plot mutual info
            obs4, factor4, color4 = "MI_", 1/np.log(2), "black";
            label4 = get_ylabel(obs4, factor4, dstring=which_imp);
            S2_vs_time = np.zeros((len(times),params["NFM"]),dtype=float);
            for ti in range(len(times)):
                S2_vs_time[ti] = np.load(dfile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(times[ti]));
            ax.plot(times, factor4*S2_vs_time[:,which_imp],color=color4, linestyle=mylinestyle);
        
    # formatting
    ax3 = ax.twinx();
    ax3.yaxis.set_label_position("left");
    ax3.spines.left.set_position(("axes", -0.2));
    ax3.spines.left.set(alpha=0.0);
    ax3.set_yticks([])
    # label later -> on right side
    ax4 = ax.twinx();
    ax4.yaxis.set_label_position("right");
    ax4.spines.right.set_position(("axes", 1.0));
    ax4.spines.right.set(alpha=1.0);
    ax4.set_yticks([])
    ax3.set_ylabel(label4, color=color4, fontsize=fontsize1); # labels (S1+S2)^2 on left
    ax4.set_ylabel(label3, color=color3, fontsize=fontsize1); # labels s_j^z on right
    ax.set_xlabel("Time $(\hbar/t_l)$", fontsize = fontsize1);
    ax.set_title( open(datafiles[0]+"_arrays/"+obs2+"title.txt","r").read().splitlines()[0][1:]);
    for tick in ticks1: ax.axhline(tick,linestyle=(0,(5,5)),color="gray");
   
    # show
    plt.tight_layout();
    plt.show();
    
elif(case in [5,6]): # left lead, SR, right lead occupancy as a function of time
    if(case in [6]): difference=True;
    else: difference = False;
    
    # axes
    fig, ax = plt.subplots();

    # plot observables for EACH datafile
    for dfile in datafiles:
        if("singlet" in dfile): mylinestyle = "dashed"; ticks1 = (0.0,0.5,1.0);
        elif("triplet" in dfile): mylinestyle = "solid"; ticks1 = (0.0,0.5,1.0);
        else: mylinestyle = "solid"; ticks1 = (-1.0,-0.5,0.0,0.5,1.0);
        print("\n>>>",mylinestyle,"=",dfile)

        # time evolution params
        params = json.load(open(dfile+".txt"));
        Nupdates, tupdate = params["Nupdates"]-update0, params["tupdate"];
        print("\nUpdate time = {:.2f}".format(params["tupdate"]));
        times = np.zeros((Nupdates+1,),dtype=float); 
        for ti in range(len(times)):
            times[ti] = (update0 + ti)*tupdate;
            
        # occ vs time
        NL, NFM, NR = params["NL"], params["NFM"], params["NR"];
        Nsites = NL+NFM+NR; 
        yjs_vs_time = np.zeros((len(times),Nsites),dtype=float);
        for ti in range(len(times)):
            yjs_vs_time[ti] = np.load(dfile+"_arrays/"+obs2+"yjs_time{:.2f}.npy".format(times[ti]));

        # break up occupancies
        yjL_vs_time = np.sum(yjs_vs_time[:,:NL], axis=1);
        yjSR_vs_time = np.sum(yjs_vs_time[:,NL:NL+NFM], axis=1);
        yjR_vs_time = np.sum(yjs_vs_time[:,NL+NFM:], axis=1);
        if(difference): # only plot change in occupancy
            print("LL n(0) = {:.4f}".format(yjL_vs_time[0]));
            yjL_vs_time = yjL_vs_time - yjL_vs_time[0];
            print("SR n(0) = {:.4f}".format(yjSR_vs_time[0]));
            yjSR_vs_time = yjSR_vs_time - yjSR_vs_time[0];
            print("RL n(0) = {:.4f}".format(yjR_vs_time[0]));
            yjR_vs_time = yjR_vs_time - yjR_vs_time[0];
        
        # plot occupancies
        ax.plot(times, yjL_vs_time,color=color1,linestyle=mylinestyle);
        ax.plot(times, yjSR_vs_time,color=color2,linestyle=mylinestyle);
        ax.plot(times, yjR_vs_time,color=color3,linestyle=mylinestyle);
        
    # formatting
    if(difference):
        label1 = "$\Delta n_{L}(t)$";
        label3 = "$\Delta n_{R}(t)$";
    else: 
        label1 = "$n_{L}(t)$";
        label3 = "$n_{R}(t)$";
    ax.set_ylabel(label1, color=color1, fontsize=fontsize1);
    ax.set_xlabel("Time $(\hbar/t_l)$", fontsize = fontsize1);
    ax.set_title( open(datafiles[0]+"_arrays/"+obs2+"title.txt","r").read().splitlines()[0][1:]);
    for tick in ticks1: ax.axhline(tick,linestyle=(0,(5,5)),color="gray");
    
    # right hand y axis label
    ax3 = ax.twinx();
    ax3.yaxis.set_label_position("right");
    ax3.spines.right.set_position(("axes", 1.0));
    ax3.spines.right.set(alpha=1.0);
    ax3.set_yticks([])
    ax3.set_ylabel(label3, color=color3, fontsize=fontsize1); 
    
    # show
    plt.tight_layout();
    plt.show();

if(case in [10,11]): # animate time evol
    datafile = datafiles[0];
    params = json.load(open(datafile+".txt"));
    if(case in [11]): plot_S2 = True;
    else: plot_S2 = False; 
    
    # axes
    fig, ax = plt.subplots();
    for tick in ticks1: ax.axhline(tick,linestyle=(0,(5,5)),color="gray");
    ax.set_yticks(ticks1);
    ax.set_xlabel("$j(d)$", fontsize=fontsize1);
    ax.set_title( open(datafile+"_arrays/"+obs2+"title.txt","r").read().splitlines()[0][1:]);
    
    # time evolution params
    Nupdates, tupdate = params["Nupdates"]-update0, params["tupdate"];
    print("\nUpdate time = {:.2f}".format(params["tupdate"]));
    times = np.zeros((Nupdates+1,),dtype=float);
    for ti in range(len(times)):
        times[ti] = (update0 + ti)*tupdate;

    # set up impurity spin animation
    xds = np.load(datafile+"_arrays/"+obs1+"xjs_time{:.2f}.npy".format(update0*tupdate));
    yds = np.load(datafile+"_arrays/"+obs1+"yjs_time{:.2f}.npy".format(update0*tupdate));
    impurity_sz, = ax.plot(xds, factor1*yds, marker=mark1, color=color1, markersize=linewidth1**2);
    ax.set_ylabel(get_ylabel(obs1, factor1), color=color1, fontsize=fontsize1);
    time_annotation = ax.annotate("Time = {:.2f}".format(update0*tupdate), (0.0,-0.96),fontsize=fontsize1);

    # set up charge density animation
    xjs = np.load(datafile+"_arrays/"+obs2+"xjs_time{:.2f}.npy".format(update0*tupdate));
    yjs = np.load(datafile+"_arrays/"+obs2+"yjs_time{:.2f}.npy".format(update0*tupdate));
    charge_density = ax.fill_between(xjs, factor2*yjs, color=color2);
    ax2 = ax.twinx();
    ax2.set_yticks([]);
    ax2.set_ylabel(get_ylabel(obs2, factor2), color=color2, fontsize=fontsize1);

    # set up spin density animation
    xjs_3 = np.load(datafile+"_arrays/"+obs3+"xjs_time{:.2f}.npy".format(update0*tupdate));
    yjs_3 = np.load(datafile+"_arrays/"+obs3+"yjs_time{:.2f}.npy".format(update0*tupdate));
    spin_density, = ax.plot(xjs_3, factor3*yjs_3, marker=mark3, color=color3);
    ax3 = ax.twinx();
    ax3.yaxis.set_label_position("left");
    ax3.spines.left.set_position(("axes", -0.15));
    ax3.spines.left.set(alpha=0.0);
    ax3.set_yticks([])
    ax3.set_ylabel(get_ylabel(obs3, factor3), color=color3, fontsize=fontsize1);

    if(plot_S2): # plot (S1+S2)^2 /2
        obs4, factor4, color4, mark4 = "S2_", 0.5, "black", "^";
        xds_4 = np.load(datafile+"_arrays/"+obs4+"xjs_time{:.2f}.npy".format(update0*tupdate));
        yds_4 = np.load(datafile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(update0*tupdate));
    else: # plot mutual information
        obs4, factor4, color4, mark4 = "MI_", 1/np.log(2), "black", "^";
        xds_4 = np.load(datafile+"_arrays/"+obs4+"xjs_time{:.2f}.npy".format(update0*tupdate));
        yds_4 = np.load(datafile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(update0*tupdate));
    S2, = ax.plot(xds_4, factor4*yds_4,marker=mark4,color=color4);
    ax4 = ax.twinx();
    ax4.yaxis.set_label_position("right");
    ax4.spines.right.set_position(("axes", 1.05));
    ax4.spines.right.set(alpha=0.0);
    ax4.set_yticks([])
    ax4.set_ylabel(get_ylabel(obs4, factor4), color=color4, fontsize=fontsize1);

    # time evolve observables
    plt.tight_layout();
    def time_evolution(time):
        # impurity spin
        yds_t = np.load(datafile+"_arrays/"+obs1+"yjs_time{:.2f}.npy".format(time));
        impurity_sz.set_ydata(factor1*yds_t);
        time_annotation.set_text("Time = {:.2f}".format(time));
        # charge density
        yjs_t = np.load(datafile+"_arrays/"+obs2+"yjs_time{:.2f}.npy".format(time));
        ax.collections.clear();
        charge_density_update = ax.fill_between(xjs, factor2*yjs_t, color=color2)
        charge_density.update_from(charge_density_update);
        # spin density
        yjs_3_t = np.load(datafile+"_arrays/"+obs3+"yjs_time{:.2f}.npy".format(time));
        spin_density.set_ydata(factor3*yjs_3_t);
        # (S1+S2)^2 / 2
        yds_4_t = np.load(datafile+"_arrays/"+obs4+"yjs_time{:.2f}.npy".format(time));
        S2.set_ydata(factor4*yds_4_t);

    # animate
    if(Nupdates > 0): interval = 1000*(10/Nupdates); # so total animation time is 10 sec
    elif(params["time_step"]==1.0): interval = 400;
    elif(params["time_step"]==0.5): interval = 200;
    else: interval = 500;
    ani = animation.FuncAnimation(fig, time_evolution,
                                  frames = times, interval=interval,
                                  repeat=True, blit=False);

    plt.show()
    # To save the animation, use e.g.
    #
    # ani.save("movie.mp4")
    #
    # or
    #
    # writer = animation.FFMpegWriter(
    #     fps=15, metadata=dict(artist='Me'), bitrate=1800)
    # ani.save("movie.mp4", writer=writer)


