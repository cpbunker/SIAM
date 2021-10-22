'''
Christian Bunker
M^2QM at UF
June 2021

fci_mod.py

Helpful funcs for using pySCF, pyblock3
Imports are within functions since some machines can run only pyblock3 or pyscf

pyscf/fci module:
- configuration interaction solvers of form fci.direct_x.FCI()
- diagonalize 2nd quant hamiltonians via the .kernel() method
- .kernel takes (1e hamiltonian, 2e hamiltonian, # spacial orbs, (# alpha e's, # beta e's))
- direct_nosym assumes only h_pqrs = h_rspq (switch r1, r2 in coulomb integral)
- direct_spin1 assumes h_pqrs = h_qprs = h_pqsr = h_qpsr
'''

import numpy as np
import functools
import itertools

import math


##########################################################################################################
#### conversions


def arr_to_scf(h1e, g2e, norbs, nelecs, verbose = 0):
    '''
    Converts hamiltonians in array form to scf object
    
    Args:
    - h1e, 2d np array, 1e part of siam ham
    - g2e, 2d np array, 2e part of siam ham
    - norbs, int, total num spin orbs
    - nelecs, tuple of number es, 0 due to All spin up formalism
    
    Returns: tuple of
    mol, gto.mol object which holds some physical params
    scf inst, holds physics: h1e, h2e, mo coeffs etc
    '''

    from pyscf import gto, scf
    
    # initial guess density matrices
    Pa = np.zeros(norbs)
    Pa[::2] = 1.0
    Pa = np.diag(Pa)
    
    # put everything into UHF scf object
    if(verbose):
        print("\nUHF energy calculation")
    mol = gto.M(); # geometry is meaningless
    mol.incore_anyway = True
    mol.nelectron = sum(nelecs)
    mol.spin = nelecs[1] - nelecs[0]; # in all spin up formalism, mol is never spinless!
    scf_inst = scf.UHF(mol)
    scf_inst.get_hcore = lambda *args:h1e # put h1e into scf solver
    scf_inst.get_ovlp = lambda *args:np.eye(norbs) # init overlap as identity matrix
    scf_inst._eri = g2e # put h2e into scf solver
    if( nelecs == (1,0) ):
        scf_inst.kernel(); # no dm
    else:
        scf_inst.kernel(dm0=(Pa, Pa)); # prints HF gd state but this number is meaningless
                                   # what matter is h1e, h2e are now encoded in this scf instance

    return mol, scf_inst;


def single_to_det(h1e, g2e, Nps, states, dets_interest = [], verbose = 0):
    '''
    transform h1e, g2e arrays, ie matrix elements in single particle basis rep
    to basis of slater determinants

    Args:
    - h1e, 2d np array, 1 particle matrix elements
    - g2e, 4d np array, 2 particle matrix elements
    - Nps, 1d array, number of particles of each species
    - states, list of lists of 1p basis states for each species
    - dets_interest, list of determinants to pick out matrix elements of
        only if asked
        only if dets of interest do not couple with other dets (blocked off)
    '''

    # check inputs
    assert( isinstance(Nps, np.ndarray));
    assert( isinstance(states, list));
    assert( isinstance(dets_interest, list));
    assert(len(states) == len(Nps));
    assert( states[-1][-1]+1 == np.shape(h1e)[0] );

    # 1 particle basis to N particle slater determinants
    # dets start as cartesian products
    dets = np.array([xi for xi in itertools.product(*tuple(states))]);

    if verbose: print("Det. basis:\n",dets);

    # put one particle matrix elements into determinantal matrix
    H = np.zeros((len(dets), len(dets) ));
    for deti in range(len(dets)):
        for detj in range(len(dets)):

            # how many 1p states the dets differ by, under maximum coincidence
            ndiff = 0;
            for pi in dets[deti]:
                if( pi not in dets[detj]):
                    ndiff += 1;

            if( ndiff == 0):
                
                # h1e
                for pi in dets[deti]: # sum over one particle states shared between both dets
                    H[deti, detj] += h1e[pi, pi]; # diagonal elements of 1p matrix

                # g2e
                mysum = 0.0;
                for pi in dets[deti]: # all shared states
                    for pj in dets[detj]:
                        mysum += g2e[pi, pi, pj, pj] - g2e[pi, pj, pj, pi]
                H[deti, detj] += (1/2)*mysum;

            elif( ndiff == 1):
                
                # have to figure out which two orbs are different:
                for pi in range(len(dets[deti])):
                    if dets[deti,pi] not in dets[detj]: whichi = pi; # index
                for pj in range(len(dets[detj])):
                    if dets[detj,pj] not in dets[deti]: whichj = pj; # index
                    
                # have to figure out fermi sign
                deltais = [abs(whichi - whichj)]
                for el in dets[deti]:
                    if el in dets[detj]:
                        deltais.append(abs(np.argmax(dets[detj] == el) - np.argmax(dets[deti] == el)));
                sign = np.power(-1, np.sum(deltais )/2 );

                # h1e
                H[deti, detj] += sign*h1e[dets[deti, whichi], dets[detj, whichj]];

                # g2e
                mysum = 0.0;
                for pi in dets[deti][dets[deti] != whichi]: # all shared orbs
                    mysum += g2e[dets[deti,whichi],dets[detj,whichj],pi,pi] - g2e[dets[deti,whichi],pi,pi,dets[detj,whichj]];
                H[deti, detj] += sign*mysum;

            elif( ndiff == 2):

                # have to figure out which two orbs are different:
                for pi2 in range(len(dets[deti])):
                    if dets[deti,pi2] not in dets[detj]: whichi2 = pi2;
                for pi1 in range(len(dets[deti])):
                    if dets[deti,pi1] not in dets[detj] and pi1 != whichi2: whichi1 = pi1;
                for pj2 in range(len(dets[deti])):
                    if dets[deti,pj2] not in dets[detj]: whichj2 = pj2;
                for pj1 in range(len(dets[deti])):
                    if dets[deti,pj1] not in dets[detj] and pj1 != whichj2: whichj1 = pj1;

                # have to figure out fermi sign
                deltais = [abs(whichi1 - whichj1),abs(whichi2-whichj2)]
                for el in dets[deti]:
                    if el in dets[detj]:
                        deltais.append(abs(np.argmax(dets[detj] == el) - np.argmax(dets[deti] == el)));
                sign = np.power(-1, np.sum(deltais )/2 );

                # no h1e contribution

                # g2e
                #print(dets[deti,whichi1],dets[detj,whichj1],dets[deti,whichi2],dets[detj,whichj2]);
                H[deti,detj] += sign*g2e[dets[deti,whichi1],dets[detj,whichj1],dets[deti,whichi2],dets[detj,whichj2]];
                H[deti,detj] += -sign*g2e[dets[deti,whichi1],dets[detj,whichj2],dets[deti,whichi2],dets[detj,whichj1]];
                
                
            else: pass; # otherwise det matrix element is zero

    # if requested, choose dets of interest only
    if(len(dets_interest)):

        # make sure requested dets are valid
        for det in dets_interest:
            assert(det in dets);
        dets_interest = np.array(dets_interest);

        # get indices of dets of interest
        is_interest = [];
        for deti in range(len(dets)): # all determinants
            for det in dets_interest: # only ones equal to one of interest
                if not np.any(dets[deti] - det):
                    is_interest.append(deti);

        # check that requested dets do not couple to other dets
        for deti in range(len(dets)): # all determinants
            for det in dets_interest: # only ones equal to one of interest
                if not np.any(dets[deti] - det):
                    coupling = H[deti];
                    for cindex in range(len(coupling)):
                        assert(coupling[cindex] == 0 or cindex in is_interest); # ensure that nonzero elements couple to other states of interest only

        # transfer desired matrix elements
        newH = np.zeros((len(is_interest),len(is_interest) ));
        for i in range(len(is_interest)):
            for j in range(len(is_interest)):
                newH[i,j] += H[is_interest[i], is_interest[j] ];
        H = newH;
        
    return H;


def scf_to_arr(mol, scf_obj):
    '''
    Converts physics of an atomic/molecular system, as contained in an scf inst
    ie produced by passing molecular geometry object mol to
    - scf.RHF(mol) restricted hartree fock
    - scf.UHF(mol) unrestricted hartree fock
    - scf.RKS(mol).run() restricted Kohn sham
    - etc
    to ab initio hamiltonian arrays h1e and g2e
    '''

    from pyscf import ao2mo

    # unpack scf object
    hcore = scf_obj.get_hcore();
    coeffs = scf_obj.mo_coeff;
    norbs = np.shape(coeffs)[0];

    # convert to h1e and h2e array reps in molecular orb basis
    h1e = np.dot(coeffs.T, hcore @ coeffs);
    g2e = ao2mo.restore(1, ao2mo.kernel(mol, coeffs), norbs);

    return h1e, g2e;


def fd_to_mpe(fd, bdim_i, cutoff = 1e-9):
    '''
    Convert physics contained in an FCIDUMP object or file to a Matrix
    Product Expectation (MPE) for doing DMRG

    Args:
    fd, a pyblock3.fcidump.FCIDUMP object, or filename of such an object
    bdim_i, int, initial bond dimension of the MPE

    Returns:
    MPE object
    '''

    from pyblock3 import fcidump, hamiltonian, algebra
    from pyblock3.algebra.mpe import MPE

    # convert fcidump to hamiltonian obj
    if( isinstance(fd, string) ): # fd is file, must be read
        hobj = hamiltonian.Hamiltonian(FCIDUMP().read(fd), flat=True);
    else: # fcidump obj already
        h_obj = hamiltonian.Hamiltonian(fd, flat=True);

    # Matrix Product Operator
    h_mpo = h_obj.build_qc_mpo();
    h_mpo, _ = h_mpo.compress(cutoff = cutoff);
    psi_mps = h_obj.build_mps(bdim_i);

    # MPE
    return MPE(psi_mps, h_mpo, psi_mps);
    


def direct_FCI(h1e, h2e, norbs, nelecs, nroots = 1, verbose = 0):
    '''
    solve gd state with direct FCI
    '''

    from pyscf import fci
    
    cisolver = fci.direct_spin1.FCI();
    E_fci, v_fci = cisolver.kernel(h1e, h2e, norbs, nelecs, nroots = nroots);
    if(verbose):
        print("\nDirect FCI energies, zero bias, norbs = ",norbs,", nelecs = ",nelecs);
        print("- E = ",E_fci);

    return E_fci, v_fci;


def scf_FCI(mol, scf_inst, nroots = 1, verbose = 0):
    '''
    '''

    from pyscf import fci, ao2mo

    # init ci solver with ham from molecule inst
    cisolver = fci.direct_uhf.FCISolver(mol);

    # get unpack from scf inst
    h1e = scf_inst.get_hcore(mol);
    norbs = np.shape(h1e)[0];
    nelecs = (mol.nelectron,0);

    # slater determinant coefficients
    mo_a = scf_inst.mo_coeff[0]
    mo_b = scf_inst.mo_coeff[1]
   
    # since we are in UHF formalism, need to split all hams by alpha, beta
    # but since everything is spin blind, all beta matrices are zeros
    h1e_a = functools.reduce(np.dot, (mo_a.T, h1e, mo_a))
    h1e_b = functools.reduce(np.dot, (mo_b.T, h1e, mo_b))
    h2e_aa = ao2mo.incore.general(scf_inst._eri, (mo_a,)*4, compact=False)
    h2e_aa = h2e_aa.reshape(norbs,norbs,norbs,norbs)
    h2e_ab = ao2mo.incore.general(scf_inst._eri, (mo_a,mo_a,mo_b,mo_b), compact=False)
    h2e_ab = h2e_ab.reshape(norbs,norbs,norbs,norbs)
    h2e_bb = ao2mo.incore.general(scf_inst._eri, (mo_b,)*4, compact=False)
    h2e_bb = h2e_bb.reshape(norbs,norbs,norbs,norbs)
    h1e_tup = (h1e_a, h1e_b)
    h2e_tup = (h2e_aa, h2e_ab, h2e_bb)
    
    # run kernel to get exact energy
    E_fci, v_fci = cisolver.kernel(h1e_tup, h2e_tup, norbs, nelecs, nroots = nroots)
    if(verbose):
        print("\nFCI from UHF, zero bias, norbs = ",norbs,", nelecs = ",nelecs);
        print("- E = ", E_fci);

    return E_fci, v_fci;


def arr_to_eigen(h1e, g2e, nelecs, verbose = 0):

    norbs = np.shape(h1e)[0];

    # to scf
    mol, scfo = arr_to_scf(h1e, g2e, norbs, nelecs);

    # to eigenstates
    e, v = scf_FCI(mol, scfo, nroots = norbs, verbose = verbose);

    return e,v;


def arr_to_initstate(h1e, g2e, nleads, nelecs, ndots, verbose = 0):

    norbs = np.shape(h1e)[0];
    imp_i = [nleads[0]*2, nleads[0]*2 + 2*ndots - 1 ];
    
    # get scf 
    mol, dotscf = arr_to_scf(h1e, g2e, norbs, nelecs, verbose = verbose);
    
    # from scf instance, do FCI, get exact gd state of equilibrium system
    E_fci, v_fci = scf_FCI(mol, dotscf, verbose = verbose);

    return E_fci, v_fci;


def kw_to_state(kw, nleads, nelecs, ndots, tl = 1.0, verbose = 0):
    '''
    Given a system setup defd by nleads, nelecs, ndots

    Generate a desired state as gd state of certain ham for system
    '''

    import ops

    norbs = 2*(sum(nleads)+ndots);

    if( kw == "dota" ):
        # dot has up electron
        # down spread over rest of system

        # params
        assert(ndots == 1);
        B = 100*tl;
        params = tl, tl, tl, 0.0, 0.0, 0.0, 0.0, -B, 0.0;

        # create system from params
        h1e, g2e, _ = ops.dot_hams(nleads, nelecs, ndots, params,"", verbose = verbose);
        mol, dotscf = arr_to_scf(h1e, g2e, norbs, nelecs, verbose = verbose);

        # desired state is gd state of system
        E0, v0 = scf_FCI(mol, dotscf, verbose = verbose);

        return v0, h1e, g2e;

    elif( kw == "dotb" ):
        # dot has down electron
        # up spread over rest of system

        # params
        assert(ndots == 1);
        B = 100*tl;
        params = tl, tl, tl, 0.0, 0.0, 0.0, 0.0, B, 0.0;

        # create system from params
        h1e, g2e, _ = ops.dot_hams(nleads, nelecs, ndots, params,"", verbose = verbose);
        mol, dotscf = arr_to_scf(h1e, g2e, norbs, nelecs, verbose = verbose);

        # desired state is gd state of system
        E0, v0 = scf_FCI(mol, dotscf, verbose = verbose);

        return v0, h1e, g2e;

    else: assert(False);
        

def vec_to_obs(vec, h1e, g2e, nleads, nelecs, ndots, verbose = 0):

    import td_fci
    
    norbs = np.shape(h1e)[0];
    imp_i = [nleads[0]*2, nleads[0]*2 + 2*ndots - 1 ];

    # get scf 
    mol, dotscf = arr_to_scf(h1e, g2e, norbs, nelecs, verbose = verbose);

    # do trivial time propagation
    init_str, obs = td_fci.kernel(h1e, g2e, vec, mol, dotscf, 0.0, 1.0, imp_i, 1.0, verbose = verbose);

    # put observables in str form for easy printing
    obs_str = "\n \t Occ = "+str(np.real(obs[6:6+sum(nleads)+ndots].T) );
    obs_str += "\n \t Sz = "+str(np.real(obs[6+sum(nleads)+ndots:-1].T) );
    obs_str += "\n \t Concur = "+str(np.real(obs[-1]));
    
    return obs, obs_str;


##########################################################################################################
#### exec code

if __name__ == "__main__":

    import ops

    # test 1p -> det conversion on kondo
    h1e = np.zeros((4,4));
    g2e = ops.h_kondo_2e(1.0,0.5);
    states_1p = [[0,1],[2,3]]; # spin states each particle can occupy

    # 1e ham, 2e ham, num particles
    interest = [[0,3],[1,2]]; # can pick out certain dets if desired
    Hdet = single_to_det(h1e, g2e,  np.array([1,1]), states_1p, dets_interest = interest, verbose = 5);
    print(Hdet);