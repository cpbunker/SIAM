#### dmrg utils
import numpy as np
import itertools

def print_H_alpha(H) -> None:
    assert(len(np.shape(H)) == 4);
    numj = np.shape(H)[0];
    for i in range(numj):
        for j in [max(0,i-1),i,min(numj-1,i+1)]:
            print("H["+str(i)+","+str(j)+"] =\n",H[i,j,:,:]);

def get_h1e(n_mols,s_mols,spatial_orbs,mytm, myB_mm, myB_elec, myJH, myJK, debug = 0) -> np.ndarray:
    '''
    make the 1body and 2body parts of the 2nd qu'd ham
    The Ham is Kumar 2017 Eqs (1)-(3)
    We only have 1 electron so all the interactions are 1body
    Electron has n_loc_dof channels which account for mol spin dofs as well
    Args:
    -mytm, hopping between mols
    -myB_mm, zeeman strength for the mol spins. Contains g*\mu_B !
    -myB_elec, zeeman strength for the electron. Contains g*\mu_B !
    -myJH, Heisenberg exchange between mol spins
    -myJK, Kondo exchange between elec and mol spins

    '''
    assert s_mols == 1/2; # have to add factors of sqrt(s) on S^\pm otherwise!
    assert(myJK == 0); # since adding it is turned off
    
    # return var
    mol_projections = tuple(np.linspace(-s_mols,s_mols,int(2*s_mols+1))[::-1]);
    mol_states = np.array([x for x in itertools.product(*(n_mols*(mol_projections,)))]);
    n_loc_dof = 2*len(mol_states);
    n_sys_orbs = spatial_orbs;
    h1e = np.zeros((n_sys_orbs, n_sys_orbs, n_loc_dof, n_loc_dof));

    #### fermionic terms
    # spin-independent hopping between n.n. sys orbs
    for sysi in range(n_sys_orbs-1):
        # iter over local dofs (up, down, etc)
        for loci in range(n_loc_dof):
            h1e[sysi,sysi+1,loci,loci] += -mytm; 
            h1e[sysi+1,sysi,loci,loci] += -mytm;
    if(n_sys_orbs > 2) and False: # last to first hopping
        for loci in range(n_loc_dof): 
            h1e[0,-1,loci,loci] += -mytm; 
            h1e[-1,0,loci,loci] += -mytm;

    #### spin terms

    # Zeeman terms
    if(debug): print("Zeeman"); 
    for sysi in range(n_sys_orbs):
        # have to iter over local dofs paticle-by-particle
        # iter over all (2s+1)^n_mols many-body mol spin states
        for mol_statei in range(len(mol_states)):
            Sztot = sum(mol_states[mol_statei]);
            # iter over electron spin 
            for sigma in range(2):
                loci = 2*mol_statei+sigma;
                h1e[sysi,sysi,loci,loci] += myB_elec*(1/2-sigma) + myB_mm*Sztot;
                if(debug and sysi == 0): print("->",loci,1/2-sigma,mol_states[mol_statei],h1e[sysi,sysi,loci,loci]);

    # Heisenberg - regardless of elec location, couples mol spins
    if(debug): print("Heisenberg"); 
    for sysi in range(n_sys_orbs):

        # iter over many-body mol spin states twice
        for mol_statei in range(len(mol_states)):
            for mol_statej in range(len(mol_states)):
                # difference between states
                n_different = np.count_nonzero(mol_states[mol_statei]-mol_states[mol_statej]);
                if(n_different in [0,2]):

                    # iter over ind'l mols in spin states twice
                    for mola in range(n_mols):
                        for molb in range(mola):
                            # nearest neighbors, first-last
                            if(mola - molb == 1 or (mola == n_mols-1) and molb == 0):
                                
                                # quantum numbers
                                Szi_a = mol_states[mol_statei][mola];
                                Szi_b = mol_states[mol_statei][molb];
                                Szj_a = mol_states[mol_statej][mola];
                                Szj_b = mol_states[mol_statej][molb];

                                # S^z_a S^z_b - couples state to itself
                                if(mol_statei == mol_statej):
                                    # add term to both elec spin channels
                                    for sigma in range(2):
                                        loci = 2*mol_statei+sigma;
                                        h1e[sysi,sysi,loci,loci] += myJH*Szi_a*Szi_b;

                                # S^+_a S^-_b couples spin flipped states
                                if(Szi_a - Szj_a==1 and Szi_b-Szj_b==-1):
                                    if(debug and sysi == 0): print("->",2*mol_statei,mol_states[mol_statei],2*mol_statej,mol_states[mol_statej]);
                                    # add term to both elec spin channels
                                    for sigma in range(2):
                                        loci = 2*mol_statei+sigma;
                                        locj = 2*mol_statej+sigma;
                                        h1e[sysi,sysi,loci,locj] += (1/2)*myJH;
                                        # hc
                                        h1e[sysi,sysi,locj,loci] += (1/2)*myJH;
    return h1e;
    # Kondo exchange - couples elec to molecule it is on
    if(debug): print("Kondo");
    for moli in range(n_mols):

        # iter over many-body mol spin states twice
        for mol_statei in range(len(mol_states)):
            for mol_statej in range(len(mol_states)):
                # difference between states
                n_different = np.count_nonzero(mol_states[mol_statei]-mol_states[mol_statej]);
                if(n_different in [0,1]):
                
                    # S^z - couples state to itself
                    if(mol_statei == mol_statej):
                        for sigma in range(2):
                            loci = 2*mol_statei+sigma;
                            h1e[moli,moli,loci,loci] += myJK*mol_states[mol_statei][moli]*(1/2-sigma);

                    # S^+ - couples statei to statej with moli flipped up by one
                    if(mol_states[mol_statei][moli]+1 == mol_states[mol_statej][moli]):
                        # all other have to be the same
                        if(n_different == 1):
                            if debug: print("->",2*mol_statei,mol_states[mol_statei],2*mol_statej,mol_states[mol_statej]);
                            # couple statei with elec up to statej wth elec down
                            h1e[moli,moli,2*mol_statei,2*mol_statej+1] += (1/2)*myJK;
                            # hc
                            h1e[moli,moli,2*mol_statej+1,2*mol_statei] += (1/2)*myJK;

    # return
    return h1e;

def get_SaSigb(n_mols,s_mols,spatial_orbs,aindex,bindex) -> np.ndarray:
    '''
    Get the operator mol spin S_a dotted into elec spin sigma on site b
    For calculating F_ab (Kumar Eq (5)
    '''
    assert s_mols == 1/2; # have to add factors of sqrt(s) on S^\pm otherwise!
    mol_projections = tuple(np.linspace(-s_mols,s_mols,int(2*s_mols+1))[::-1]);
    mol_states = np.array([x for x in itertools.product(*(n_mols*(mol_projections,)))]);
    
    # construct as 4d in the spatial orbs, mol_states basis
    SaSigb = np.zeros((spatial_orbs,spatial_orbs,2*len(mol_states),2*len(mol_states)));

    # iter over many-body mol spin states twice
    for mol_statei in range(len(mol_states)):
        for mol_statej in range(len(mol_states)):
            # difference between states
            n_different = np.count_nonzero(mol_states[mol_statei]-mol_states[mol_statej]);
            if(n_different in [0,1]):
                
                # S^z - couples state to itself
                if(mol_statei == mol_statej):
                    for sigma in range(2):
                        loci = 2*mol_statei+sigma;
                        SaSigb[aindex,bindex,loci,loci] += mol_states[mol_statei][aindex]*(1/2-sigma);

                # S^+ - couples statei to statej with moli flipped up by one
                if(mol_states[mol_statei][aindex]+1 == mol_states[mol_statej][aindex]):
                    # all other have to be the same
                    if(n_different == 1):
                        # couple statei with elec up to statej wth elec down
                        SaSigb[aindex,bindex,2*mol_statei,2*mol_statej+1] += (1/2);
                        # hc
                        SaSigb[aindex,bindex,2*mol_statej+1,2*mol_statei] += (1/2);

    # return
    return SaSigb;
        

def get_SaSb(n_mols,s_mols,spatial_orbs,aindex,bindex) -> np.ndarray:
    '''
    Get the operator mol spin S_a dotted into mol spin S_b
    For calculating D_ab (Kumar Eq (5)
    '''
    assert s_mols == 1/2; # have to add factors of sqrt(s) on S^\pm otherwise!
    mol_projections = tuple(np.linspace(-s_mols,s_mols,int(2*s_mols+1))[::-1]);
    mol_states = np.array([x for x in itertools.product(*(n_mols*(mol_projections,)))]);
    if(aindex == bindex): raise ValueError;
    
    # construct as 4d in the spatial orbs, mol_states basis
    SaSb = np.zeros((spatial_orbs,spatial_orbs,len(mol_states),len(mol_states)));

    # iter over many-body mol spin states twice
    for mol_statei in range(len(mol_states)):
        for mol_statej in range(len(mol_states)):
            # difference between states
            n_different = np.count_nonzero(mol_states[mol_statei]-mol_states[mol_statej]);
            if(n_different in [0,2]):
                               
                # quantum numbers
                Szi_a = mol_states[mol_statei][aindex];
                Szi_b = mol_states[mol_statei][bindex];
                Szj_a = mol_states[mol_statej][aindex];
                Szj_b = mol_states[mol_statej][bindex];

                # S^z_a S^z_b - couples state to itself
                if(mol_statei == mol_statej):
                    # add term to all spatial blocks
                    for spacei in range(spatial_orbs):
                        SaSb[spacei,spacei,mol_statei,mol_statej] += Szi_a*Szi_b;

                # S^+_a S^-_b couples spin flipped states
                if(Szi_a - Szj_a==1 and Szi_b-Szj_b==-1):
                    #print("->",2*mol_statei,mol_states[mol_statei],2*mol_statej,mol_states[mol_statej]);
                    # add term to all spatial blocks
                    for spacei in range(spatial_orbs):
                        SaSb[spacei,spacei,mol_statei,mol_statej] += (1/2);
                        # hc
                        SaSb[spacei,spacei,mol_statej,mol_statei] += (1/2);

    # return                       
    return SaSb;
    
def get_SaSb_sigma(n_mols,s_mols,spatial_orbs,aindex,bindex) -> np.ndarray:
    '''
    Get the operator mol spin S_a dotted into mol spin S_b
    For calculating D_ab (Kumar Eq (5)
    '''
    assert s_mols == 1/2; # have to add factors of sqrt(s) on S^\pm otherwise!
    mol_projections = tuple(np.linspace(-s_mols,s_mols,int(2*s_mols+1))[::-1]);
    mol_states = np.array([x for x in itertools.product(*(n_mols*(mol_projections,)))]);
    if(aindex == bindex): raise ValueError;
    
    # construct as 4d in the spatial orbs, mol_states basis
    SaSb = np.zeros((spatial_orbs,spatial_orbs,2*len(mol_states),2*len(mol_states)));

    # iter over many-body mol spin states twice
    for mol_statei in range(len(mol_states)):
        for mol_statej in range(len(mol_states)):
            # difference between states
            n_different = np.count_nonzero(mol_states[mol_statei]-mol_states[mol_statej]);
            if(n_different in [0,2]):
                               
                # quantum numbers
                Szi_a = mol_states[mol_statei][aindex];
                Szi_b = mol_states[mol_statei][bindex];
                Szj_a = mol_states[mol_statej][aindex];
                Szj_b = mol_states[mol_statej][bindex];

                # S^z_a S^z_b - couples state to itself
                if(mol_statei == mol_statej):
                    # add term to all spatial blocks
                    for spacei in range(spatial_orbs):
                        # for both elec spins
                        for sigma in [0,1]:
                            #print("->",2*mol_statei,mol_states[mol_statei],2*mol_statej,mol_states[mol_statej]);
                            SaSb[spacei,spacei,2*mol_statei+sigma,2*mol_statej+sigma] += Szi_a*Szi_b;

                # S^+_a S^-_b couples spin flipped states
                if(Szi_a - Szj_a==1 and Szi_b-Szj_b==-1):
                    #print("->",2*mol_statei,mol_states[mol_statei],2*mol_statej,mol_states[mol_statej]);
                    # add term to all spatial blocks
                    for spacei in range(spatial_orbs):
                    # for both elec spins
                        for sigma in [0,1]:
                            SaSb[spacei,spacei,2*mol_statei+sigma,2*mol_statej+sigma] += (1/2);
                            # hc
                            SaSb[spacei,spacei,2*mol_statej+sigma,2*mol_statei+sigma] += (1/2);

    # return                       
    return SaSb;


