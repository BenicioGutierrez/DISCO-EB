import pylinger_thermo_jax as pthermo

import numpy as np
from scipy.integrate import solve_ivp

import jax
# from jax import config
# config.update("jax_enable_x64", True)
import jax.numpy as jnp
import jax_cosmo.scipy.interpolate as jaxinterp
import scipy.interpolate as scipyinterp
from jax_cosmo.scipy.integrate import romb
from functools import partial

@jax.jit
def ninu1( a : float, amnu: float, nq : int = 1000, qmax : float = 30.) -> tuple[float, float]:
    """ computes the neutrino density and pressure of one flavour of massive neutrinos
        in units of the mean density of one flavour of massless neutrinos

    Args:
        a (float): scale factor
        amnu (float): neutrino mass in units of neutrino temperature (m_nu*c**2/(k_B*T_nu0).
        nq (int, optional): number of integration points. Defaults to 1000.
        qmax (float, optional): maximum momentum. Defaults to 30..

    Returns:
        tuple[float, float]: rho_nu/rho_nu0, p_nu/p_nu0
    """

    # const = 7 * np.pi**4 / 120
    const = 5.682196976983475
    
    # q is the comoving momentum in units of k_B*T_nu0/c.
    # Integrate up to qmax and then use asymptotic expansion for remainder.
    dq   = qmax / nq
    q    = dq * jnp.arange(1,nq+1)
    aq   = a * amnu / q
    v    = 1 / jnp.sqrt(1 + aq**2)
    qdn  = dq * q**3 / (jnp.exp(q) + 1)
    dum1 = qdn / v
    dum2 = qdn * v
    
    rho_spline = jaxinterp.InterpolatedUnivariateSpline(q, dum1)
    rhonu = rho_spline.integral(0, qmax)
    p_spline = jaxinterp.InterpolatedUnivariateSpline(q, dum2)
    pnu = p_spline.integral(0, qmax)

    # Apply asymptotic corrrection for q>qmax and normalize by relativistic
    # energy density.
    rhonu = (rhonu / dq + dum1[-1] / dq) / const
    pnu = (pnu / dq + dum2[-1] / dq) / const / 3
    
    return rhonu[0], pnu[0]


def ninu1_numoy( a : float, amnu: float, nq : int = 1000, qmax : float = 30.) -> tuple[float, float]:
    """ computes the neutrino density and pressure of one flavour of massive neutrinos
        in units of the mean density of one flavour of massless neutrinos

    Args:
        a (float): scale factor
        amnu (float): neutrino mass in units of neutrino temperature (m_nu*c**2/(k_B*T_nu0).
        nq (int, optional): number of integration points. Defaults to 1000.
        qmax (float, optional): maximum momentum. Defaults to 30..

    Returns:
        tuple[float, float]: rho_nu/rho_nu0, p_nu/p_nu0
    """

    # const = 7 * np.pi**4 / 120
    const = 5.682196976983475
    
    # q is the comoving momentum in units of k_B*T_nu0/c.
    # Integrate up to qmax and then use asymptotic expansion for remainder.
    dq   = qmax / nq
    q    = dq * jnp.arange(1,nq+1)
    aq   = a * amnu / q
    v    = 1 / jnp.sqrt(1 + aq**2)
    qdn  = dq * q**3 / (jnp.exp(q) + 1)
    dum1 = qdn / v
    dum2 = qdn * v
    
    rho_spline = scipyinterp.InterpolatedUnivariateSpline(q, dum1)
    rhonu = rho_spline.integral(0, qmax)
    p_spline = scipyinterp.InterpolatedUnivariateSpline(q, dum2)
    pnu = p_spline.integral(0, qmax)

    # Apply asymptotic corrrection for q>qmax and normalize by relativistic
    # energy density.
    rhonu = (rhonu / dq + dum1[-1] / dq) / const
    pnu = (pnu / dq + dum2[-1] / dq) / const / 3
    
    return rhonu[0], pnu[0]


@jax.jit
def nu_perturb_jax( a : float, amnu: float, psi0, psi1, psi2, nq : int = 1000, qmax : float = 30.):
    """ Compute the perturbations of density, energy flux, pressure, and
        shear stress of one flavor of massive neutrinos, in units of the mean
        density of one flavor of massless neutrinos, by integrating over 
        momentum.

    Args:
        a (float): scale factor
        amnu (float): neutrino mass in units of neutrino temperature (m_nu*c**2/(k_B*T_nu0).
        psi0 (_type_): 
        psi1 (_type_): _description_
        psi2 (_type_): _description_
        nq (int, optional): _description_. Defaults to 1000.
        qmax (float, optional): _description_. Defaults to 30..

    Returns:
        _type_: drhonu, dpnu, fnu, shearnu
    """
    nqmax0 = len(psi0)
    qmax0  = nqmax0 - 0.5
    # const = 7 * np.pi**4 / 120
    const = 5.682196976983475

    g1 = jnp.zeros((nqmax0+1))
    g2 = jnp.zeros((nqmax0+1))
    g3 = jnp.zeros((nqmax0+1))
    g4 = jnp.zeros((nqmax0+1))
    q  = (jnp.arange(1,nqmax0+1) - 0.5)  # so dq == 1
    qq = jnp.arange(0,nqmax0+1)  # so dq == 1
    # q.at[0].set(0.0)

    aq = a * amnu / q
    v = 1 / jnp.sqrt(1 + aq**2)
    qdn = q**3 / (jnp.exp(q) + 1)
    g1 = g1.at[1:].set( qdn * psi0 / v )
    g2 = g2.at[1:].set( qdn * psi0 * v )
    g3 = g3.at[1:].set( qdn * psi1 )
    g4 = g4.at[1:].set( qdn * psi2 * v )

    g1_sp = jaxinterp.InterpolatedUnivariateSpline(qq, g1)
    g01 = g1_sp.integral(0, qmax0)[0]
    g2_sp = jaxinterp.InterpolatedUnivariateSpline(qq, g2)
    g02 = g2_sp.integral(0, qmax0)[0]
    g3_sp = jaxinterp.InterpolatedUnivariateSpline(qq, g3)
    g03 = g3_sp.integral(0, qmax0)[0]
    g4_sp = jaxinterp.InterpolatedUnivariateSpline(qq, g4)
    g04 = g4_sp.integral(0, qmax0)[0]

    # Apply asymptotic corrrection for q>qmax0
    drhonu = (g01 + g1[-1] * 2 / qmax) / const
    dpnu = (g02 + g2[-1] * 2 / qmax) / const / 3
    fnu = (g03 + g3[-1] * 2 / qmax) / const
    shearnu = (g04 + g4[-1] * 2 / qmax) / const * 2 / 3

    return drhonu, dpnu, fnu, shearnu


def nu_perturb_numpy( a : float, amnu: float, psi0, psi1, psi2, nq : int = 1000, qmax : float = 30.):
    """ Compute the perturbations of density, energy flux, pressure, and
        shear stress of one flavor of massive neutrinos, in units of the mean
        density of one flavor of massless neutrinos, by integrating over 
        momentum.

    Args:
        a (float): scale factor
        amnu (float): neutrino mass in units of neutrino temperature (m_nu*c**2/(k_B*T_nu0).
        psi0 (_type_): 
        psi1 (_type_): _description_
        psi2 (_type_): _description_
        nq (int, optional): _description_. Defaults to 1000.
        qmax (float, optional): _description_. Defaults to 30..

    Returns:
        _type_: drhonu, dpnu, fnu, shearnu
    """
    nqmax0 = len(psi0)
    qmax0  = nqmax0 - 0.5
    # const = 7 * np.pi**4 / 120
    const = 5.682196976983475

    g1 = np.zeros((nqmax0+1))
    g2 = np.zeros((nqmax0+1))
    g3 = np.zeros((nqmax0+1))
    g4 = np.zeros((nqmax0+1))
    q  = (np.arange(1,nqmax0+1) - 0.5)  # so dq == 1
    qq = np.arange(0,nqmax0+1)  # so dq == 1
    # q.at[0].set(0.0)

    aq = a * amnu / q
    v = 1 / np.sqrt(1 + aq**2)
    qdn = q**3 / (np.exp(q) + 1)
    g1[1:] = qdn * psi0 / v
    g2[1:] = qdn * psi0 * v
    g3[1:] = qdn * psi1 
    g4[1:] = qdn * psi2 * v

    g1_sp = scipyinterp.InterpolatedUnivariateSpline(qq, g1)
    g01 = g1_sp.integral(0, qmax0)
    g2_sp = scipyinterp.InterpolatedUnivariateSpline(qq, g2)
    g02 = g2_sp.integral(0, qmax0)
    g3_sp = scipyinterp.InterpolatedUnivariateSpline(qq, g3)
    g03 = g3_sp.integral(0, qmax0)
    g4_sp = scipyinterp.InterpolatedUnivariateSpline(qq, g4)
    g04 = g4_sp.integral(0, qmax0)

    # Apply asymptotic corrrection for q>qmax0
    drhonu = (g01 + g1[-1] * 2 / qmax) / const
    dpnu = (g02 + g2[-1] * 2 / qmax) / const / 3
    fnu = (g03 + g3[-1] * 2 / qmax) / const
    shearnu = (g04 + g4[-1] * 2 / qmax) / const * 2 / 3

    return drhonu, dpnu, fnu, shearnu

# @partial(jax.jit, static_argnames=("params",))
@jax.jit
def dtauda_(a, grhom, grhog, grhor, Omegam, OmegaL, Omegak, Neff, Nmnu, rhonu_spline):
    """Derivative of conformal time with respect to scale factor"""
    grho2 = grhom * Omegam * a 
    + (grhog + grhor*(Neff+Nmnu*rhonu_spline(a))) 
    + grhom * OmegaL * a**4 
    + grhom * Omegak * a**2
    return jnp.sqrt(3.0 / grho2)

class cosmo:

    def __init__(self, *, Omegam: float, Omegab: float, OmegaL: float, H0: float, Tcmb: float, YHe: float, Neff: float, Nmnu: int = 0, mnu: float = 0.0, rtol: float = 1e-5, atol: float = 1e-7, order: int = 5):
        c2ok = 1.62581581e4 # K / eV
        amin = 1e-9
        amax = 1.01
        num_thermo = 1000 # length of thermal history arrays

        # mean densities
        Omegak = 0.0 #1.0 - Omegam - OmegaL

        grhom = 3.3379e-11 * H0**2 # critical density at z=0 in h^2/Mpc^3
        grhog = 1.4952e-13 * Tcmb**4 # photon density in h^2/Mpc^3
        grhor = 3.3957e-14 * Tcmb**4 # neutrino density per flavour in h^2/Mpc^3
        adotrad = 2.8948e-7 * Tcmb**2 # Hubble during radiation domination

        self.param = {
            'Omegam': Omegam,
            'Omegab': Omegab,
            'OmegaL': OmegaL,
            'Omegac': Omegam - Omegab,
            'Omegak': Omegak,
            'H0': H0,
            'Tcmb': Tcmb,
            'YHe': YHe,
            'Neff': Neff,
            'Nmnu': Nmnu,
            'mnu': mnu,
            'grhom': grhom,
            'grhog': grhog,
            'grhor': grhor,
            'adotrad': adotrad,
            'amnu': mnu * c2ok / Tcmb, # conversion factor for Neutrinos masses (m_nu*c**2/(k_B*T_nu0)
            'amin' : amin,
            'amax' : amax,
        }
        # Compute the scale factor linearly spaced in log(a)
        a = jnp.geomspace(amin, amax, num_thermo)

        # Compute the neutrino density and pressure
        rhonu = jnp.zeros_like(a)
        pnu = jnp.zeros_like(a)
        for i in range(num_thermo):
            rhonu_, pnu_ = ninu1(a[i], self.param['amnu'] )
            rhonu = rhonu.at[i].set(rhonu_)
            pnu = pnu.at[i].set(pnu_)

        rhonu_spline =  jaxinterp.InterpolatedUnivariateSpline(a, rhonu)
        self.param['rhonu_of_a_spline'] = rhonu_spline
        self.param['pnu_of_a_spline']   = jaxinterp.InterpolatedUnivariateSpline(a, pnu)
        
        # self.r1 = jaxinterp.InterpolatedUnivariateSpline(self.a, jnp.log(self.rhonu))
        # self.p1 = jaxinterp.InterpolatedUnivariateSpline(self.a, jnp.log(self.pnu))
        
        # self.dr1 = lambda a : self.r1.derivative(a)
        # self.ddr1 = lambda a : self.r1.derivative(a,n=2)
        # self.dp1 = lambda a : self.p1.derivative(a)

        taumin = amin / adotrad
        taumax = taumin + romb( lambda loga: jnp.exp(loga) * dtauda_(jnp.exp(loga),grhom, grhog, grhor, Omegam, OmegaL, Omegak, Neff, Nmnu, rhonu_spline), jnp.log(amin), jnp.log(amax) )
        self.param['taumin'] = taumin
        self.param['taumax'] = taumax

        # self.th = pthermo.thermal_history(taumin=self.taumin,taumax=self.taumax,cp=self,N=1000)
        th = pthermo.compute( taumin=taumin, taumax=taumax, nthermo=num_thermo, Tcmb=Tcmb,
                             YHe=YHe, H0=H0, Omegab=Omegab, Omegam=Omegam, OmegaL=OmegaL,
                             Neff=Neff, Nmnu=Nmnu, rhonu_sp=rhonu_spline )
        
        self.param['cs2_of_tau_spline']   = jaxinterp.InterpolatedUnivariateSpline(th['tau'], th['cs2'])
        self.param['tempb_of_tau_spline'] = jaxinterp.InterpolatedUnivariateSpline(th['tau'], th['tb'])
        self.param['xe_of_tau_spline']    = jaxinterp.InterpolatedUnivariateSpline(th['tau'], th['xe'])
        self.param['a_of_tau_spline']     = jaxinterp.InterpolatedUnivariateSpline(th['tau'], th['a'])
        self.param['tau_of_a_spline']     = jaxinterp.InterpolatedUnivariateSpline(th['a'], th['tau'])
        
        
        