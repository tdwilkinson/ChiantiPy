import os
import numpy as np
from scipy import interpolate
from matplotlib.tri import Triangulation, LinearTriInterpolator
import ChiantiPy.tools.data as chdata
import ChiantiPy.tools.util as util
import ChiantiPy.tools.io as chio
import ChiantiPy.tools.constants as const
import ChiantiPy.Gui as chgui
ip = chdata.Ip
MasterList = chdata.MasterList
#import chianti
class continuum:
    '''
    The top level class for continuum calculations.

    includes methods for the calculation of the free-free and free-bound continua.
    '''
    def __init__(self, ionStr,  temperature, abundance=0, abundanceName=0, em=0, verbose=0):
        nameDict = util.convertName(ionStr)
        self.Z = nameDict['Z']
        self.Ion = nameDict['Ion']
        self.IonStr = ionStr
        self.Dielectronic = 0
        self.Defaults = chdata.Defaults
        self.AbundanceName = self.Defaults['abundfile']
        self.IoneqName = self.Defaults['ioneqfile']
        #
        #  ip in eV, reading Ip of next lower level, needed for freeBound

        if self.Ion == 1:
            if verbose:
                print(' for %s this is the neutral ions an does not produce a continuum'%(ionStr))
            return
        #  the Ip is only relevant to the free-free methods
#        self.Ip = ip[self.Z-1, self.Ion-1]
        self.Ipr = ip[self.Z-1, self.Ion-2]
        #
        if type(temperature) == float and temperature > 0.:
            self.Temperature = np.asarray(temperature,'float64')
        elif type(temperature) == list or type(temperature) == tuple or type(temperature) == np.ndarray:
            temperature = np.asarray(temperature, 'float64')
            self.Temperature = temperature
        #
        if abundance:
            self.Abundance = abundance
        elif abundanceName:
            if abundanceName in sorted(chdata.Abundance.keys()):
                self.AbundanceName = abundanceName
                self.Abundance = chdata.Abundance[self.AbundanceName]['abundance'][self.Z-1]
            else:
                abundChoices = sorted(chdata.Abundance.keys())
#                for one in wvl[topLines]:
#                    wvlChoices.append('%12.3f'%(one))
                abundChoice = chgui.gui.selectorDialog(abundChoices,label='Select Abundance name')
                abundChoice_idx = abundChoice.selectedIndex
                self.AbundanceName = abundChoices[abundChoice_idx[0]]
                abundanceName = self.AbundanceName
                print(' Abundance chosen:  %s '%(self.AbundanceName))
                self.Abundance = chdata.Abundance[self.AbundanceName]['abundance'][self.Z-1]
        else:
            self.AbundanceName = self.Defaults['abundfile']
            self.Abundance = chdata.Abundance[self.AbundanceName]['abundance'][self.Z-1]
        #
        self.ioneqOne()
        #
        if type(em) == int and em == 0:
            em = np.ones_like(self.Temperature, 'float64')
            self.Em = em
        elif type(em) == float and em > 0.:
            em = np.ones_like(self.Temperature, 'float64')*em
            self.Em = em
        elif type(em) == list or type(em) == tuple or type(em) == np.ndarray:
            em = np.asarray(em, 'float64')
            self.Em = em
        #
        #----------------------------------------------------------------------------------------
        #
    def freeBoundEmiss(self, wvl, verner=1):
        '''Calculates the free-bound (radiative recombination) continuum emissivity of an ion.

        Uses the Gaunt factors of Karzas, W.J, Latter, R, 1961, ApJS, 6, 167
        for recombination to the ground level, the photoionization cross sections of
        Verner and Yakovlev, 1995, A&ASS, 109, 125
        are used to develop the free-bound cross section
        provides emissivity = ergs cm^-2 s^-1 str^-1 Angstrom ^-1 for an individual ion
        does not include the elemental abundance or ionization fraction
        the specified ion is the target ion'''
        #
        wvl = np.asarray(wvl, 'float64')
        temperature = self.Temperature
        #
        # data for the recombined ion
        #
        if hasattr(self, 'Fblvl'):
            fblvl = self.Fblvl
        else:
            fblvlname = util.zion2filename(self.Z,self.Ion-1)+'.fblvl'
            self.Fblvl = chio.fblvlRead(fblvlname)
            fblvl = self.Fblvl
            if 'errorMessage' in fblvl.keys():
                self.FreeBound = fblvl
                return
        #
        #  need some data for the recombining ion
        #
        if hasattr(self, 'rFblvl'):
            rFblvl = self.rFblvl
        else:
            if self.Ion == self.Z+1:
                # then we looking for the bare ion
                rFblvl = {'mult':[1., 1.]}
            else:
                rfblvlname = util.zion2filename(self.Z,self.Ion)+'.fblvl'  # previously self.Ion)
                self.rFblvl = chio.fblvlRead(rfblvlname)
                rFblvl = self.rFblvl
            if 'errorMessage' in rFblvl.keys():
                self.FreeBound = rFblvl
                return
        #
        #  6/9/2010 the recombining ion is the present ion
        #
        nlvls = len(fblvl['lvl'])
        # pqn = principle quantum no. n
        pqn = fblvl['pqn']
        # l is angular moment quantum no. L
        l = fblvl['l']
        # energy level in inverse cm
        ecm = fblvl['ecm']
        # statistical weigths/multiplicities
        mult = fblvl['mult']
        multr = rFblvl['mult']
        #
        #  Ipr
        #
        # for the ionization potential, must use that of the recombined ion
#        Ipr = ip[self.Z-1, self.Ion-2]
#        ipcm = self.Ip/const.invCm2Ev
        iprcm = self.Ipr/const.invCm2Ev
        #for i in range(nlvls):
            #print(' lvl %5i ecm %12.3e Ip-wvl %12.4f  Ipr-wvl %12.4f '%(i, ecm[i], 1.e+8/(ipcm-ecm[i]), 1.e+8/(iprcm-ecm[i])))
        #
        # get karzas-latter Gaunt factors
        if hasattr(self,'Klgfb'):
            klgfb = self.Klgfb
        else:
            self.Klgfb = chio.klgfbRead()
            klgfb = self.Klgfb
        #
        #
        nWvl = wvl.size
        nTemp = temperature.size
        #
        if verner:
            lvl1 = 1
        else:
            lvl1 = 0
            #
        if (nTemp > 1) and (nWvl > 1):
            mask = np.zeros((nlvls,nTemp,nWvl),'Bool')
            fbrate = np.zeros((nlvls,nTemp,nWvl),'float64')
            expf = np.zeros((nlvls,nTemp,nWvl),'float64')
            ratg = np.zeros((nlvls),'float64')
            if verner:
                self.vernerCross(wvl)
                vCross = self.VernerCross
            #
            ratg[0] = float(mult[0])/float(multr[0])
            iprLvlEv = self.Ipr - const.invCm2Ev*ecm[0]
            iprLvlErg = const.ev2Erg*iprLvlEv
            iprLvlCm = (iprcm - ecm[0])
            for itemp in range(nTemp):
                mask[0,itemp] = 1.e+8/wvl < (iprcm - ecm[0])
                expf[0,itemp] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature[itemp]))
                fbrate[0,itemp] = (const.planck*const.light/(1.e-8*wvl))**5*const.verner*ratg[0]*expf[0,itemp]*vCross/temperature[itemp]**1.5
            for ilvl in range(lvl1,nlvls):
                iprLvlEv = self.Ipr - const.invCm2Ev*ecm[ilvl]
                iprLvlErg = const.ev2Erg*iprLvlEv
                scaledE = np.log(const.ev2Ang/(iprLvlEv*wvl))
                thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                spl = interpolate.splrep(klgfb['pe'], thisGf)
                gf = np.exp(interpolate.splev(scaledE, spl))
                ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
            #
                for itemp in range(nTemp):
                    expf[ilvl,itemp] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature[itemp]))
                    mask[ilvl,itemp] = 1.e+8/wvl < (iprcm - ecm[ilvl])
                    fbrate[ilvl,itemp] = const.freeBound*ratg[ilvl]*(iprLvlErg**2/float(pqn[ilvl]))*gf*expf[ilvl,itemp]/(temperature[itemp]**1.5*(wvl)**2)
            fbrma = np.ma.array(fbrate)
            fbrma.mask =  mask
            fbrma.fill_value = 0.
            fbRate = (fbrma).sum(axis=0)
            fbRate.fill_value = 0.
            self.FreeBoundEmiss = {'emiss':fbRate.data, 'temperature':temperature,'wvl':wvl}
            #
        elif (nTemp == 1) and (nWvl > 1):
            mask = np.zeros((nlvls,nWvl),'Bool')
            fbrate = np.zeros((nlvls,nWvl),'float64')
            expf = np.zeros((nlvls,nWvl),'float64')
            #ratg = np.zeros((nlvls),'float64')
            if verner:
                self.vernerCross(wvl)
                vCross = self.VernerCross
                #
            ratg = float(mult[0])/float(multr[0])
            iprLvlEv = self.Ipr - const.invCm2Ev*ecm[0]
            iprLvlErg = const.ev2Erg*iprLvlEv
            iprLvlCm = (iprcm - ecm[0])
            #
            mask[0] = 1.e+8/wvl < (iprcm - ecm[0])
            expf[0] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
            fbrate[0] = (const.planck*const.light/(1.e-8*wvl))**5*const.verner*ratg*expf[0]*vCross/temperature**1.5
            for ilvl in range(lvl1,nlvls):
                iprLvlEv = self.Ipr - const.invCm2Ev*ecm[ilvl]
                iprLvlErg = const.ev2Erg*iprLvlEv
                iprLvlCm = (iprcm - ecm[ilvl])
                mask[ilvl] = 1.e+8/wvl <  iprLvlCm
    #                #                print ' ilvl, ipLvlEv = ', ilvl, ipLvlEv
                scaledE = np.log(const.ev2Ang/(iprLvlEv*wvl))
                thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                spl = interpolate.splrep(klgfb['pe'], thisGf)
                gf = np.exp(interpolate.splev(scaledE, spl))
                ratg = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
                expf[ilvl] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
                fbrate[ilvl] = const.freeBound*ratg*expf[ilvl]*(iprLvlErg**2/float(pqn[ilvl]))*gf/(temperature**1.5*(wvl)**2)
            fbrma = np.ma.array(fbrate)
            fbrma.mask =  mask
            fbrma.fill_value = 0.
            fbRate = fbrma.sum(axis=0)
            fbRate.fill_value = 0.
            # factor of 1.e-8 converts to Angstrom^-1, otherwise it would be cm^-1
            #            fbRate = (expf*fbrma).sum(axis=0)
            #fbRma = np.ma.array(fbrate.sum(axis=0), mask=mask, fill_value=0.)
            #            fbRate.fill_value = 0.
            self.FreeBoundEmiss = {'fbRate':fbRate, 'emiss':fbRate.data, 'temperature':temperature,'wvl':wvl, 'mask':mask, 'expf':expf,'vCross':vCross}
        else:
            #  this is the case of a single wavelength, not going to do this anymore
            #mask = np.zeros((nlvls,nTemp),'Bool')
            #fbrate = np.zeros((nlvls,nTemp),'float64')
            #expf = np.zeros((nlvls,nTemp),'float64')
            #ratg = np.zeros((nlvls),'float64')
            #if verner:
                #self.vernerCross(wvl)
                #vCross = self.VernerCross
            ##
            #mask[0] = 1.e+8/wvl < (ipcm - ecm[0])
            #ratg[0] = float(mult[0])/float(multr[0])
            #ipLvlEv = self.Ip - const.invCm2Ev*ecm[0]
            #ipLvlErg = const.ev2Erg*ipLvlEv
            #expf[0] = np.exp((ipLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
            #fbrate[0] = (const.planck*const.light/(1.e-8*wvl))**5*const.verner*ratg[0]*expf[0]*vCross/temperature**1.5
            #for ilvl in range(lvl1,nlvls):
                ## scaled energy is relative to the ionization potential of each individual level
                #ipLvlEv = self.Ip - const.invCm2Ev*ecm[ilvl]
                #scaledE = np.log(const.ev2Ang/(ipLvlEv*wvl))
                #thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                #spl = interpolate.splrep(klgfb['pe'], thisGf)
                #gf = np.exp(interpolate.splev(scaledE, spl))
                #mask[ilvl] = 1.e+8/wvl < (ipcm - ecm[ilvl])
                #ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
                #ipLvlErg = const.ev2Erg*ipLvlEv
                #expf[ilvl] = np.exp((ipLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
                #fbrate[ilvl] = const.freeBound*ratg[ilvl]*(ipLvlErg**2/float(pqn[ilvl]))*expf[ilvl]*gf/(temperature**1.5*(wvl)**2)
            #fbrma = np.ma.array(fbrate)
            #fbrma.mask =  mask
            #fbrma.fill_value = 0.
            ## factor of 1.e-8 converts to Angstrom^-1, otherwise it would be cm^-1
            #fbRate = (fbrma).sum(axis=0)
            #fbRate.fill_value = 0.
            #self.FreeBoundEmiss = {'emiss':fbRate.data, 'temperature':temperature,'wvl':wvl}
            self.FreeBoundEmiss = {'errorMessage':' this is the case of a single wavelength'}
            #
            # ----------------------------------------------------------------------------
            #
    def freeBound(self, wvl, verner=1):
        '''
        to calculate the free-bound (radiative recombination) continuum rate coefficient of an ion, where
        the ion is taken to be the recombined ion,
        including the elemental abundance and the ionization equilibrium population
        uses the Gaunt factors of Karzas, W.J, Latter, R, 1961, ApJS, 6, 167
        for recombination to the ground level, the photoionization cross sections of
        Verner and Yakovlev, 1995, A&ASS, 109, 125
        are used to develop the free-bound cross section
        includes the elemental abundance and the ionization fraction
        provides emissivity = ergs cm^-2 s^-1 str^-1 Angstrom ^-1
        '''
        wvl = np.asarray(wvl, 'float64')
        temperature = self.Temperature
        #
        if hasattr(self, 'IoneqOne'):
            gIoneq = self.IoneqOne
        else:
            self.ioneqOne()
            gIoneq = self.IoneqOne
        #
        # put in freefree to go through ipymspectrum
        if not np.any(gIoneq) > 0:
            self.FreeBound = {'errorMessage':' no non-zero values of ioneq'}
            return
        #
        em = self.Em
        #
        # the recombined ion contains that data for fblvl
        #
        if hasattr(self,'Fblvl'):
            fblvl = self.Fblvl
        else:
            fblvlname = util.zion2filename(self.Z,self.Ion-1)+'.fblvl'
            self.Fblvl = chio.fblvlRead(fblvlname)
            fblvl = self.Fblvl
            # in case there is no fblvl file
            if 'errorMessage' in fblvl.keys():
                self.FreeBound = fblvl
                return
        #
        #  need data for the current/recombining ion
        #
        if hasattr(self,'rFblvl'):
            rFblvl = self.rFblvl
        else:
            if self.Ion == self.Z + 1:
                # this is a bare ion
                rFblvl = {'mult':[1., 1.]}
            else:
                rfblvlname = util.zion2filename(self.Z,self.Ion)+'.fblvl'
                self.rFblvl = chio.fblvlRead(rfblvlname)
                rFblvl = self.rFblvl
            if 'errorMessage' in rFblvl.keys():
                self.FreeBound = rFblvl
                return
        #
        #gIoneq = self.IoneqOne
        #
        #
        abund = self.Abundance
        #
        #
        nlvls = len(fblvl['lvl'])
        # pqn = principle quantum no. n
        pqn = np.asarray(fblvl['pqn'], 'float64')
        # l is angular moment quantum no. L
        l = fblvl['l']
        # energy level in inverse cm
        ecm = fblvl['ecm']
        # statistical weigths/multiplicities
        mult = fblvl['mult']
        multr = rFblvl['mult']
#       ipcm = self.Ip/const.invCm2Ev
        #
        #
        # for the ionization potential, must use that of the recombined ion
        #
        iprcm = self.Ipr/const.invCm2Ev
        #
        # get karzas-latter Gaunt factors
        if hasattr(self,'Klgfb'):
            klgfb = self.Klgfb
        else:
            self.Klgfb = chio.klgfbRead()
            klgfb = self.Klgfb
        #
        nWvl = wvl.size
        nTemp = temperature.size
        #
        if verner:
            lvl1 = 1
        else:
            lvl1 = 0
            #
        nWvl = wvl.size
        nTemp = temperature.size
        #
        #
        if (nTemp > 1) and (nWvl > 1):
            mask = np.zeros((nlvls,nTemp,nWvl),'Bool')
            fbrate = np.zeros((nlvls,nTemp,nWvl),'float64')
            expf = np.zeros((nlvls,nTemp,nWvl),'float64')
            ratg = np.zeros((nlvls),'float64')
            #fbRate = np.zeros((nTemp,nWvl),'float64')
            if verner:
                self.vernerCross(wvl)
                vCross = self.VernerCross
            ratg[0] = float(mult[0])/float(multr[0])
            iprLvlEv = self.Ipr - const.invCm2Ev*ecm[0]
            iprLvlErg = const.ev2Erg*iprLvlEv
            iprLvlCm = (iprcm - ecm[0])
            for itemp in range(nTemp):
                mask[0,itemp] = 1.e+8/wvl < (iprcm - ecm[0])
                expf[0,itemp] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature[itemp]))
                fbrate[0,itemp] = em[itemp]*(const.planck*const.light/(1.e-8*wvl))**5*const.verner*gIoneq[itemp]*ratg[0]*expf[0,itemp]*vCross/temperature[itemp]**1.5
            for ilvl in range(lvl1,nlvls):
                iprLvlEv = self.Ipr - const.invCm2Ev*ecm[ilvl]
                iprLvlErg = const.ev2Erg*iprLvlEv
                scaledE = np.log(const.ev2Ang/(iprLvlEv*wvl))
                thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                spl = interpolate.splrep(klgfb['pe'], thisGf)
                gf = np.exp(interpolate.splev(scaledE, spl))
                ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
            #
                for itemp in range(nTemp):
                    expf[ilvl] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature[itemp]))
                    expf[ilvl,itemp] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature[itemp]))
                    mask[ilvl,itemp] = 1.e+8/wvl < (iprcm - ecm[ilvl])
                    fbrate[ilvl,itemp] = em[itemp]*const.freeBound*gIoneq[itemp]*ratg[ilvl]*(iprLvlErg**2/float(pqn[ilvl]))*gf*expf[ilvl,itemp]/(temperature[itemp]**1.5*(wvl)**2)
            fbrma = np.ma.array(fbrate)
            fbrma.mask =  mask
            fbrma.fill_value = 0.
            fbRate = (fbrma).sum(axis=0)
            fbRate.fill_value = 0.
            self.FreeBound = {'rate':abund*fbRate.data, 'temperature':temperature,'wvl':wvl,'em':em}
            #
        elif (nTemp == 1) and (nWvl > 1):
            mask = np.zeros((nlvls,nWvl),'Bool')
            fbrate = np.zeros((nlvls,nWvl),'float64')
            expf = np.zeros((nlvls,nWvl),'float64')
            ratg = np.zeros((nlvls),'float64')
            if verner:
                self.vernerCross(wvl)
                vCross = self.VernerCross
            # mask is true for bad values
            ratg[0] = float(mult[0])/float(multr[0])
            iprLvlEv = self.Ipr - const.invCm2Ev*ecm[0]
            iprLvlErg = const.ev2Erg*iprLvlEv
            iprLvlCm = (iprcm - ecm[0])
            #
            mask[0] = 1.e+8/wvl < (iprcm - ecm[0])
            expf[0] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
            fbrate[0] = em*(const.planck*const.light/(1.e-8*wvl))**5*const.verner*ratg[0]*expf[0]*vCross/temperature**1.5
            #
            for ilvl in range(lvl1,nlvls):
                iprLvlEv = self.Ipr - const.invCm2Ev*ecm[ilvl]
                iprLvlErg = const.ev2Erg*iprLvlEv
                iprLvlCm = (iprcm - ecm[ilvl])
                # scaled energy is relative to the ionization potential of each individual level
                scaledE = np.log(const.ev2Ang/(iprLvlEv*wvl))
                thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                spl = interpolate.splrep(klgfb['pe'], thisGf)
                gf = np.exp(interpolate.splev(scaledE, spl))
                mask[ilvl] = 1.e+8/wvl < iprLvlCm
                ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
                expf[ilvl] = np.exp((iprLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
                fbrate[ilvl] = em*const.freeBound*ratg[ilvl]*(iprLvlErg**2/float(pqn[ilvl]))*expf[ilvl]*gf/(temperature**1.5*(wvl)**2)
            fbrma = np.ma.array(fbrate)
            fbrma.mask =  mask
            fbrma.fill_value = 0.
            # factor of 1.e-8 converts to Angstrom^-1, otherwise it would be cm^-1
            fbRate = abund*gIoneq*fbrma.sum(axis=0)
            fbRate.fill_value = 0.
            self.FreeBound = {'rate':fbRate.data, 'temperature':temperature,'wvl':wvl}
        #elif (nTemp > 1) and (nWvl == 1):
        else:
            #mask = np.zeros((nlvls,nTemp),'Bool')
            #fbrate = np.zeros((nlvls,nTemp),'float64')
            #expf = np.zeros((nlvls,nTemp),'float64')
            #ratg = np.zeros((nlvls),'float64')
            #if verner:
                #self.vernerCross(wvl)
                #vCross = self.VernerCross
            #mask[0] = 1.e+8/wvl < (ipcm - ecm[0])
            #ratg[0] = float(mult[0])/float(multr[0])
            #ipLvlEv = self.Ip - const.invCm2Ev*ecm[0]
            #ipLvlErg = const.ev2Erg*ipLvlEv
            #expf[0] = np.exp((ipLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
            #fbrate[0] = self.Em[itemp]*(const.planck*const.light/(1.e-8*wvl))**5*const.verner*ratg[0]*expf[0]*vCross/temperature**1.5
            #for ilvl in range(lvl1,nlvls):
                ## scaled energy is relative to the ionization potential of each individual level
                #ipLvlEv = self.Ip - const.invCm2Ev*ecm[ilvl]
                #scaledE = np.log(const.ev2Ang/(ipLvlEv*wvl))
                #thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                #spl = interpolate.splrep(klgfb['pe'], thisGf)
                #gf = np.exp(interpolate.splev(scaledE, spl))
                #mask[ilvl] = 1.e+8/wvl < (ipcm - ecm[ilvl])
                #ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
                #ipLvlErg = const.ev2Erg*ipLvlEv
                #expf[ilvl] = np.exp((ipLvlErg - 1.e+8*const.planck*const.light/wvl)/(const.boltzmann*temperature))
                #fbrate[ilvl] = self.Em[itemp]*const.freeBound*ratg[ilvl]*(ipLvlErg**2/float(pqn[ilvl]))*expf[ilvl]*gf/(temperature**1.5*(wvl)**2)
            #fbrma = np.ma.array(fbrate)
            #fbrma.mask =  mask
            #fbrma.fill_value = 0.
            ## factor of 1.e-8 converts to Angstrom^-1, otherwise it would be cm^-1
            #fbRate = abund*gIoneq*(fbrma).sum(axis=0)
            #fbRate.fill_value = 0.
            #self.FreeBound = {'rate':fbRate.data, 'temperature':temperature,'wvl':wvl, 'em':self.Em}
            self.FreeBoundEmiss = {'errorMessage':' this is the case of a single wavelength'}
        #
        # ----------------------------------------------------------------------------------------
        #
            #
    def freeBoundLoss(self):
        '''
        to calculate the free-bound (radiative recombination) energy loss rate coefficient of an ion,
        the ion is taken to be the recombined iion,
        including the elemental abundance and the ionization equilibrium population
        uses the Gaunt factors of Karzas, W.J, Latter, R, 1961, ApJS, 6, 167
        provides rate = ergs cm^-2 s^-1
        '''
        #
        temperature = self.Temperature
        #
        if hasattr(self, 'Fblvl'):
            fblvl = self.Fblvl
        else:
            fblvlname = util.zion2filename(self.Z,self.Ion-1)+'.fblvl'
            if os.path.isfile(fblvlname):
                self.Fblvl = chio.fblvlRead(fblvlname)
                fblvl = self.Fblvl
            else:
                self.FreeBoundLoss = {'errorMessage':' file does not exist %s .fblvl'%(fblvlname)}
                return
        #  need some data for the recombining/target ion
        #
        if hasattr(self, 'rFblvl'):
            rFblvl = self.rFblvl
        else:
            if self.Ion == self.Z + 1:
                # then we looking for the bare ion
                rFblvl = {'mult':[1., 1.]}
            else:
                rfblvlname = util.zion2filename(self.Z,self.Ion)+'.fblvl'
                if os.path.isfile(rfblvlname):
                    self.rFblvl = chio.fblvlRead(rfblvlname)
                    rFblvl = self.rFblvl
                else:
                    self.FreeBoundLoss = {'errorMessage':' file does not exist %s .fblvl'%(rfblvlname)}
                    return
        #
        gIoneq = self.IoneqOne
        #
        abund = self.Abundance
        #
        #
        nlvls = len(fblvl['lvl'])
        # pqn = principle quantum no. n
        pqn = np.asarray(fblvl['pqn'], 'float64')
        # l is angular moment quantum no. L
        l = fblvl['l']
        # energy level in inverse cm
        ecm = fblvl['ecm']
        # statistical weigths/multiplicities
        mult = fblvl['mult']
        multr = rFblvl['mult']
        #
        #
        # for the ionization potential, must use that of the recombined ion
        #
        iprcm = self.Ipr/const.invCm2Ev
        #
        # get karzas-latter Gaunt factors
        if hasattr(self, 'Klgfb'):
            klgfb = self.Klgfb
        else:
            self.Klgfb = chio.klgfbRead()
            klgfb = self.Klgfb
        #
        nTemp = temperature.size
        # statistical weigths/multiplicities
        #
        #
        #wecm=1.e+8/(ipcm-ecm)
        #
        # sometime the rFblvl file does not exist
        if 'mult' in fblvl.keys() and 'mult' in rFblvl.keys():
            #
            nlvls = len(fblvl['lvl'])
            # pqn = principle quantum no. n
            pqn = fblvl['pqn']
            # l is angular moment quantum no. L
            l = fblvl['l']
            # energy level in inverse cm
            ecm = fblvl['ecm']
            mult = fblvl['mult']
            multr = rFblvl['mult']
            fbrate = np.zeros((nlvls,nTemp),'float64')
            ratg = np.zeros((nlvls),'float64')
            for ilvl in range(nlvls):
                # scaled energy is relative to the ionization potential of each individual level
                # will add the average energy of a free electron to this to get typical photon energy to
                # evaluate the gaunt factor
                hnuEv = 1.5*const.boltzmann*temperature/const.ev2Erg
                iprLvlEv = self.Ipr - const.invCm2Ev*ecm[ilvl]
                scaledE = np.log(hnuEv/iprLvlEv)
                thisGf = klgfb['klgfb'][pqn[ilvl]-1, l[ilvl]]
                spl = interpolate.splrep(klgfb['pe'], thisGf)
                gf = np.exp(interpolate.splev(scaledE, spl))
                ratg[ilvl] = float(mult[ilvl])/float(multr[0]) # ratio of statistical weights
                iprLvlErg = const.ev2Erg*iprLvlEv
                fbrate[ilvl] = ratg[ilvl]*(iprLvlErg**2/float(pqn[ilvl]))*gf/np.sqrt(temperature)
            fbRate = abund*gIoneq*const.freeBoundLoss*(fbrate.sum(axis=0))
        else:
            fbRate = np.zeros((nTemp),'float64')
        self.FreeBoundLoss = {'rate':fbRate, 'temperature':temperature}
        #
        # ----------------------------------------------------------------------------------------
        #
    def vernerCross(self,wvl):
        '''Calculates the photoionization cross section.

        The data are from Verner and Yakovlev
        the cross section refers to the next lower ionization stage'''
        try:
            vernerDat = self.VernerDat
        except:
            self.VernerDat = chio.vernerRead()
            vernerDat = self.VernerDat
        z = self.Z
        stage = self.Ion
#        ip = self.Ip
        iprcm = self.Ipr/const.invCm2Ev
        ecm = self.Fblvl['ecm']
        #
        en = const.ev2Ang/wvl
        y = en/vernerDat['e0'][z,stage-1]
        fy= vernerDat['sig0'][z,stage-1]*((y - 1.)**2 + vernerDat['yw'][z,stage-1]**2) * y**(-5.5 - vernerDat['l'][z,stage-1] + 0.5*vernerDat['p'][z,stage-1]) * (1. + np.sqrt(y/vernerDat['ya'][z,stage-1]))**(-vernerDat['p'][z,stage-1])
#       mask = en < vernerDat['eth'][z,stage]
        # will use Chianti values for energy of ground level
        mask = (1.e+8/wvl) < (iprcm - ecm[0])
        vCross = np.ma.array(fy)
        vCross.mask = mask
        vCross.fill_value = 0.
        # cross-section will be output in cm^2
        self.VernerCross = vCross*1.e-18
        #
        # ----------------------------------------------------------------------------------------
        #
    def freeFree(self, wvl):
        '''
        Calculates the free-free emission for a single ion.

        Includes elemental abundance and ionization equilibrium population
        and the emission measure (em) if specified
        Uses Itoh where valid and Sutherland elsewhere
        '''
        em=self.Em
        temperature = self.Temperature
        nTemp = temperature.size
        #
        if self.Ion == 1:
            self.FreeFree = {'errorMessage':' freefree is not produced by neutrals'}
            return
        else:
            wvl = np.asarray(wvl, 'float64')
            ffs = self.sutherland(wvl)
            #
            ffi = self.itoh(wvl)
            ff = ffs['suthFf']
            if not 'errorMessage' in ffi.keys():
                iff = ffi['itohFf']
                itohMask = np.logical_not(iff.mask)
                ff[itohMask] = iff[itohMask]
        ff = np.asarray(ff,'float64')
        #
        if hasattr(self, 'IoneqOne'):
            gIoneq = self.IoneqOne
        else:
            self.ioneqOne()
            gIoneq = self.IoneqOne
        #
        # put in freefree to go through ipymspectrum
        if not np.any(gIoneq) > 0:
            self.FreeFree = {'errorMessage':' no non-zero values of ioneq'}
            return
        #
        if type(gIoneq) == float:
            # only one temperature specified
            if gIoneq == 0.:
                ffRate = np.zeros(wvl.size)
                self.FreeFree = {'rate':ffRate, 'temperature':self.Temperature,'wvl':wvl}
                return
        else:
            if gIoneq.sum() == 0.:
                ffRate = np.zeros((self.Temperature.size, wvl.size), 'float64')
                self.FreeFree = {'rate':ffRate, 'temperature':self.Temperature,'wvl':wvl}
                return
        #
        #for one in gIoneq.shape:
            #print('gIoneq shape = %10i'%(one))
        #for one in ff.shape:
            #print('ff shape = %10i'%(one))
        #
        if wvl.size > 1:
            #gIoneq = gIoneq.repeat(wvl.size).reshape(self.Temperature.size,wvl.size)
            #em = em.repeat(wvl.size).reshape(self.Temperature.size,wvl.size)
            #
            try:
                abund = self.Abundance
            except:
                self.AbundanceAll = util.abundanceRead(abundancename = self.AbundanceName)
                self.Abundance = self.AbundanceAll['abundance'][self.Z-1]
                abund = self.Abundance
                #
            if nTemp == 1:
                ffRate = em*const.freeFree*(self.Z)**2*abund*gIoneq*ff
            elif nTemp > 1:
                ffRate = np.zeros((nTemp,wvl.size),'float64')
                for it in range(nTemp):
                    ffRate[it] = (em[it]*const.freeFree*(self.Z)**2*abund*gIoneq[it]*ff[it])  #  .squeeze()
            self.FreeFree = {'rate':ffRate, 'temperature':self.Temperature,'wvl':wvl,'ff':ff}
        #
        # ----------------------------------------------------------------------------------------
        #
    def freeFreeEmiss(self, wvl):
        '''Calculates the free-free emissivity for a single ion.
        does not include element abundance or ionization fraction
        Uses Itoh where valid and Sutherland elsewhere'''
        if self.Ion == 1:
            self.FreeFreeEmiss = {'errorMessage':' freefree is not produced by neutrals'}
        else:
            wvl = np.asarray(wvl, 'float64')
            ffs = self.sutherland(wvl)
            ff = ffs['suthFf']
            ffi = self.itoh(wvl)
            if 'errorMessage' not in ffi.keys():
                iff = ffi['itohFf']
                itohMask = np.logical_not(iff.mask)
                ff[itohMask] = iff[itohMask]
            #
            ffRate = (const.freeFree*(self.Z)**2*ff).squeeze()
            self.FreeFree = {'rate':ffRate, 'temperature':self.Temperature,'wvl':wvl}
        #
        # ----------------------------------------------------------------------------------------
        #
    def freeFreeLoss(self):
        '''
        Calculates the total free-free emission for a single ion.

        Includes elemental abundance and ionization equilibrium population.

        Uses Itoh where valid and Sutherland elsewhere
        '''
        temperature = self.Temperature
        #print(' doing freeFreeLoss for %s'%(self.IonStr))
        #
        if self.Ion == 1:
            self.FreeFree = {'errorMessage':' freefree is not produced by neutrals'}
        else:
            #
            #   should be done with masked arrays
            #
            #if hasattr(self, 'Gffint'):
                #gffint = self.Gffint['gffint']
                #g2 = self.Gffint['g2']
            #else:
                #self.Gffint = chio.gffintRead()
                #gffint = self.Gffint['gffint']
                #g2 = self.Gffint['g2']
            ##
            #gamma2 = self.Ip*const.ev2Erg/(const.boltzmann*temperature)
             ##
            #try:
                #spl = interpolate.splrep(g2, gffint)
                #gff = interpolate.splev(np.log(gamma2), spl)
            #except:
                #print(' for %s problem with interpolate.splev(np.log(gamma2), spl)'%(self.IonStr))
                #self.FreeFreeLoss = {'rate':np.zeros_like(temperature),'temperature':temperature,'errorMessage':'problems with interpolate'}
                #return
            #
            # this is reallly close enough
            #
            gff = 1.2
            #
            if hasattr(self, 'IoneqOne'):
                gIoneq = self.IoneqOne
            else:
                self.ioneqOne()
                gIoneq = self.IoneqOne
            #
            if hasattr(self, 'Abundance'):
                abund = self.Abundance
            else:
                self.AbundanceAll = util.abundanceRead(abundancename = self.AbundanceName)
                self.Abundance = self.AbundanceAll['abundance'][self.Z-1]
                abund = self.Abundance
                #
            #print('gff min %12.e max %12.e'%(gff.min(),gff.max()))
            #if np.isnan(gff.any()):
                #ffRate = np.zeros_like(temperature)
            #else:
            ffRate = const.freeFreeLoss*(self.Z)**2*abund*gIoneq*gff*np.sqrt(temperature)
            self.FreeFreeLoss = {'rate':ffRate, 'temperature':temperature}
        #
        # ----------------------------------------------------------------------------------------
        #
    def klgfbInterp(self, wvl, n, l):
        '''A Python version of the CHIANTI IDL procedure karzas_xs.

        Interpolates free-bound gaunt factor of Karzas and Latter, (1961, Astrophysical Journal
        Supplement Series, 6, 167) as a function of wavelength (wvl).'''
        try:
            klgfb = self.Klgfb
        except:
            self.Klgfb = util.klgfbRead()
            klgfb = self.Klgfb
        # get log of photon energy relative to the ionization potential
        sclE = np.log(self.Ip/(wvl*const.ev2ang))
        thisGf = klgfb['klgfb'][n-1, l]
        spl = interpolate.splrep(klgfb['pe'], thisGf)
        gf = interpolate.splev(sclE, spl)
        return gf

        #
        # ----------------------------------------------------------------------------------------
        #
    def itoh(self, wvl):
        '''Calculates free-free emission with the free-free gaunt factors of Itoh et al. (ApJS 128, 125, 2000).

        the relativistic values are valid for 6. < log10(T) < 8.5 and -4. < log10(u) < 1.'''
        wvl = np.array(wvl, 'float64')
        try:
            itohCoef = self.ItohCoef
        except:
            self.ItohCoef = chio.itohRead()['itohCoef'][self.Z-1].reshape(11, 11)
            itohCoef = self.ItohCoef
        try:
            t = (np.log10(self.Temperature) -7.25)/1.25
        except:
            errorMessage = ' temperature undefined in continuum.itoh'
            print(errorMessage)
            return {'errorMessage':errorMessage}
        if type(self.Temperature) == float:
            nTemp = 1
        else:
            nTemp = self.Temperature.size
        #
        nWvl = wvl.size
        #
        if (nTemp > 1) and (nWvl > 1):
            u = (const.planck*const.light*1.e+8/const.boltzmann)*np.outer(1./self.Temperature, 1./wvl )
            lU = (np.log10(u) + 1.5)/2.5
            lT = (np.log10(self.Temperature) -7.25)/1.25
            g = np.zeros((nTemp, nWvl), 'float64')
            rad = np.ma.zeros((nTemp, nWvl), 'float64')
            for itemp in range(nTemp):
                for j in range(11):
                    for i in range(11):
                        g[itemp]+= itohCoef[i,j]*(lT[itemp]**i)*(lU[itemp]**j)
                rad[itemp] = (1./wvl)**2*g[itemp]*np.exp(-u[itemp])/np.sqrt(self.Temperature[itemp])
            tArray = np.zeros((1, len(self.Temperature)), 'float64')
            tArray[0] = self.Temperature
            t2Array = np.repeat(tArray.transpose(), len(wvl), axis=1)
            nonValidT1 = np.log10(t2Array) < 6.
            nonValidT2 = np.log10(t2Array) > 8.5
            nonValidT = np.logical_or(nonValidT1, nonValidT2)
            nonValidU1 = np.log10(u) < -4.
            nonValidU2 = np.log10(u) > 1.
            nonValidU = np.logical_or(nonValidU1, nonValidU2)
            nonValid = np.logical_or(nonValidT, nonValidU)
            rad.mask = nonValid
            rad.set_fill_value(0.)
            g=np.ma.array(g, mask=nonValid, fill_value=0.)
            return {'itohGff':g, 'itohFf':rad}
        elif (nTemp > 1) and (nWvl == 1):
            u = (const.planck*const.light*1.e+8/const.boltzmann)/(self.Temperature*wvl )
            lU = (np.log10(u) + 1.5)/2.5
            lT = (np.log10(self.Temperature) -7.25)/1.25
            g = np.zeros((nTemp), 'float64')
            rad = np.ma.zeros((nTemp), 'float64')
            for itemp in range(nTemp):
                for j in range(11):
                    for i in range(11):
                        g[itemp]+= itohCoef[i,j]*(lT[itemp]**i)*(lU[itemp]**j)
                rad[itemp] = (1./wvl)**2*g[itemp]*np.exp(-u[itemp])/np.sqrt(self.Temperature[itemp])
            nonValidT1 = np.log10(self.Temperature) < 6.
            nonValidT2 = np.log10(self.Temperature) > 8.5
            nonValidT = np.logical_or(nonValidT1, nonValidT2)
            nonValidU1 = np.log10(u) < -4.
            nonValidU2 = np.log10(u) > 1.
            nonValidU = np.logical_or(nonValidU1, nonValidU2)
            nonValid = np.logical_or(nonValidT, nonValidU)
            rad.mask = nonValid
            rad.set_fill_value(0.)
            g=np.ma.array(g, mask=nonValid, fill_value=0.)
            return {'itohGff':g, 'itohFf':rad}
        elif (nTemp == 1) and (nWvl > 1):
            if (np.log10(self.Temperature) < 6.) or (np.log10(self.Temperature > 8.5)):
                errorMessage ='invalid temperature in continuum.itoh()'
                return {'errorMessage':errorMessage}
            else:
                u = (const.planck*const.light*1.e+8/const.boltzmann)/(self.Temperature*wvl )
                lU = (np.log10(u) + 1.5)/2.5
                lT = (np.log10(self.Temperature) -7.25)/1.25
                g = np.zeros(nWvl, 'float64')
                rad = np.ma.zeros((nWvl), 'float64')
                for j in range(11):
                    for i in range(11):
                        g+= itohCoef[i,j]*(lT**i)*(lU**j)
                rad = np.ma.array((1./wvl)**2*g*np.exp(-u)/np.sqrt(self.Temperature), 'Float64')
                nonValidU1 = np.log10(u) < -4.
                nonValidU2 = np.log10(u) > 1.
                nonValidU = np.logical_or(nonValidU1, nonValidU2)
                nonValid = nonValidU
                rad.mask = nonValid
                rad.set_fill_value(0.)
                g=np.ma.array(g, mask=nonValid, fill_value=0.)
                return {'itohGff':g, 'itohFf':rad}
        elif (nTemp == 1) and (nWvl == 1):
            u = (const.planck*const.light*1.e+8/const.boltzmann)/(self.Temperature*wvl )
            if (np.log10(self.Temperature) < 6.) or (np.log10(self.Temperature > 8.5)):
                errorMessage ='invalid temperature in continuum.itoh()'
                return {'errorMessage':errorMessage}
            elif (np.log10(u) < -4.) or (np.log10(u) > 8.5):
                errorMessage ='invalid temperature/wavelength in continuum.itoh()'
                return {'errorMessage':errorMessage}
            else:
                u = (const.planck*const.light*1.e+8/const.boltzmann)/(self.Temperature*wvl )
                lU = (np.log10(u) + 1.5)/2.5
                lT = (np.log10(self.Temperature) -7.25)/1.25
                g = np.zeros(nWvl, 'float64')
                rad = np.ma.zeros((nWvl), 'float64')
                for j in range(11):
                    for i in range(11):
                        g+= itohCoef[i,j]*(lT**i)*(lU**j)
                rad = np.ma.array((1./wvl)**2*g*np.exp(-u)/np.sqrt(self.Temperature), 'Float64')
                nonValidU1 = np.log10(u) < -4.
                nonValidU2 = np.log10(u) > 1.
                nonValidU = np.logical_or(nonValidU1, nonValidU2)
                nonValid = nonValidU
                rad.mask = nonValid
                rad.set_fill_value(0.)
                return {'itohGff':g, 'itohFf':rad}
        #
        # - - - - - - - - - - - - - - - - - - - - - - -
        #
    def sutherland(self, wvl):
        '''Calculates the free-free continuum using the free-free gaunt factor calculations of Sutherland, 1998, MNRAS, 300, 321.

        the wavelengths (wvl) will be sorted, first thing'''
        #
        wvl = np.array(wvl, 'float64')
        nWvl = wvl.size
#       factor = 5.44436e-39
        try:
            temperature = self.Temperature
        except:
            errorMessage = ' temperature undefined in continuum.sutherland'
            print(errorMessage)
            return {'errorMessage':errorMessage}
        #  read in the gaunt factors, if necessary and get interpolator
        try:
            gffInterpolator = self.GffInterpolator
        except:
            self.Gff = chio.gffRead()
            gff = self.Gff
            iu=(np.log10(gff['u1d']) + 4.)*10.
            ig=(np.log10(gff['g21d']) + 4.)*5.
            gaunt = gff['gff']
            #tr=Triangulation(iu.flatten(),ig.flatten())
            tr = Triangulation(iu,ig)
            self.GffInterpolator = LinearTriInterpolator(tr, gaunt.flatten())
            gffInterpolator = self.GffInterpolator
            # this is the old version
            #self.Gff = chio.gffRead()
            #gff = self.Gff
            #iu=(np.log10(gff['u1d']) + 4.)*10.
            #ig=(np.log10(gff['g21d']) + 4.)*5.
            #gaunt = gff['gff']
            ##tr=Triangulation(iu.flatten(),ig.flatten())
            #tr=Triangulation(iu,ig)
            #self.GffInterpolator = tr.nn_interpolator(gaunt.flatten())
            #gffInterpolator = self.GffInterpolator
    #
        gga = np.array((float(self.Z)**2*const.ryd2erg/const.boltzmann)*(1./temperature),'float64')
        nonValidGg1 = np.log10(gga) < -4.
        nonValidGg2 = np.log10(gga) > 4.
        nonValidGg = np.logical_or(nonValidGg1, nonValidGg2)
        ggOut = np.ma.array(gga, mask = nonValidGg, fill_value=True)
        iGg = np.ma.array((np.log10(gga) + 4.)*5., mask=nonValidGg,  fill_value=0.)
        #
        if nonValidGg.sum():
            errorMessage = 'no valid temperatures in continuum.sutherland'
            print(errorMessage)
            return {'errorMessage':errorMessage}
        else:
                #iUu = np.ma.array((np.log10(uu) + 4.)*10., mask=nonValidUu,  fill_value=0.)
        #iGg = (np.log10(gg) + 4.)*5.
        #print ' iGg.shape = ',iGg, iGg.shape
            #
            nWvl = wvl.size
            nTemp = temperature.size
            #
            if (nTemp > 1) and (nWvl > 1):
                ff = np.ma.zeros((nWvl, nTemp), 'float64')
                gffOut1 = np.ma.zeros((nWvl, nTemp), 'float64')
                gffOutMask = np.zeros((nWvl, nTemp), 'Bool')
                uuOut = np.zeros((nWvl, nTemp), 'float64')
                for iwvl in range(nWvl):
                    uu = ((const.planck*const.light*1.e+8/const.boltzmann)/(wvl[iwvl]*temperature))  #.flatten()
                    nonValidUu1 = np.log10(uu) < -4.
                    nonValidUu2 = np.log10(uu) > 4.
                    nonValidUu = np.logical_or(nonValidUu1, nonValidUu2)
                    gffOutMask[iwvl] = nonValidUu
                    uuOut[iwvl] = np.ma.array(uu, mask=nonValidUu, fill_value=True)
                    iUu = np.ma.array((np.log10(uu) + 4.)*10., mask=nonValidUu,  fill_value=0.)
                    gffOut1[iwvl] = gffInterpolator(iUu, iGg)
                    wvlt = 1./(wvl[iwvl]**2*np.sqrt(temperature))  # was sortedTemperature
                    ff[iwvl] = (np.exp(-uuOut[iwvl])*gffOut1[iwvl]*wvlt)
                gffOut1.mask = gffOutMask
                gffOut1.set_fill_value(0.)
                gffOut = gffOut1.transpose()
                ff.mask = gffOutMask
                ff.set_fill_value(0.)
                return {'suthFf':ff.transpose(), 'suthGff':gffOut}
            #
            if (nTemp == 1) and (nWvl > 1):
                uu = ((const.planck*const.light*1.e+8/const.boltzmann)/(wvl*temperature))  # .flatten()
                nonValidUu1 = np.log10(uu) < -4.
                nonValidUu2 = np.log10(uu) > 4.
                nonValidUu = np.logical_or(nonValidUu1, nonValidUu2)
                gffOutMask = nonValidUu
                iUu = (np.log10(uu) + 4.)*10.
                gffOut1 = gffInterpolator(iUu, iGg.repeat(nWvl))
                wvlt = 1./(wvl**2*np.sqrt(temperature))
                ff = np.ma.array(np.exp(-uu)*gffOut1*wvlt)
                ff.mask=gffOutMask
                ff.set_fill_value(0.)
                gffOut = np.ma.array(gffOut1, mask=gffOutMask, fill_value=0.)
                return {'suthFf':ff, 'suthGff':gffOut, 'iUu':iUu, 'gffOut1':gffOut1, 'wvlt':wvlt,  'iGg':iGg.repeat(nWvl), 'gffInterpolator':gffInterpolator}
        #elif (nTemp > 1) and (nWvl == 1):
            else:
                #print ' igg.shape = ',iGg.shape
                #gffOut1 = np.ma.zeros((nTemp), 'float64')
                #gffOutMask = np.zeros((nTemp), 'Bool')
                #uuOut = np.zeros((nTemp), 'float64')
                #
                uu = (const.planck*const.light*1.e+8/const.boltzmann) /(wvl*temperature).flatten()
                nonValidUu1 = np.log10(uu) < -4.
                nonValidUu2 = np.log10(uu) > 4.
                nonValidUu = np.logical_or(nonValidUu1, nonValidUu2)
                gffOutMask = nonValidUu
                uuOut = np.ma.array(uu, mask=nonValidUu, fill_value=True)
                #iUu = np.ma.array((np.log10(uu) + 4.)*10., mask=nonValidUu,  fill_value=0.)
                iUu = (np.log10(uu) + 4.)*10.
                #print ' iUu.shape = ',iUu.shape
                gffOut1 = gffInterpolator(iUu, iGg.flatten())
                #
                wvlt = 1./(wvl**2*np.sqrt(temperature))
                ff1 = np.exp(-uuOut)*gffOut1*wvlt
                ff = np.ma.array(ff1, mask=gffOutMask, fill_value=0.)
                gffOut = np.ma.array(gffOut1, mask=gffOutMask, fill_value=0.)
        return {'suthFf':ff, 'suthGff':gffOut}
            #elif (nTemp == 1) and (nWvl == 1):
        ##iGg = (np.log10(gg) + 4.)*5.
        #uu = (const.planck*const.light*1.e+8/const.boltzmann)/(wvl*temperature)
        #nonValidUu1 = np.log10(uu) < -4.
        #nonValidUu2 = np.log10(uu) > 4.
        #nonValidUu = np.logical_or(nonValidUu1, nonValidUu2)
        #if not nonValidUu:
            #iUu = (np.log10(uu) + 4.)*10.
            #gffOut = gffInterpolator(iUu, iGg)
            #wvlt = 1./(wvl**2*np.sqrt(temperature))
            #ff = np.exp(-uu)*gffOut*wvlt
            #return {'suthFf':ff, 'suthGff':gffOut}
        #else:
            #errorMessage = 'invalid Temperature/Wavlength in continuum.sutherland'
            #print(errorMessage)
            #return {'errorMessage':errorMessage}
        #
        # ----------------------------------------------------------------------------------------
        #
    def ioneqOne(self):
        '''Provide the ionization equilibrium for the selected ion as a function of temperature.
        returned in self.IoneqOne
        this is a duplicate of the method ion.ioneqOne '''
        #
        try:
            temperature = self.Temperature
        except:
            return
        #
        try:
            ioneqAll = self.IoneqAll
        except:
            self.IoneqAll = chio.ioneqRead(ioneqname = self.Defaults['ioneqfile'])
            ioneqAll=self.IoneqAll
        #
        ioneqTemperature = ioneqAll['ioneqTemperature']
        Z=self.Z
        Ion=self.Ion
        Dielectronic=self.Dielectronic
        ioneqOne = np.zeros_like(temperature)
        #
        thisIoneq=ioneqAll['ioneqAll'][Z-1,Ion-1-Dielectronic].squeeze()
#        thisIoneq = self.Ioneq
        gioneq=thisIoneq > 0.
        goodt1=self.Temperature >= ioneqTemperature[gioneq].min()
        goodt2=self.Temperature <= ioneqTemperature[gioneq].max()
        goodt=np.logical_and(goodt1,goodt2)
        y2=interpolate.splrep(np.log(ioneqTemperature[gioneq]),np.log(thisIoneq[gioneq]),s=0)
        #
        if goodt.sum() > 0:
            if self.Temperature.size > 1:
                gIoneq=interpolate.splev(np.log(self.Temperature[goodt]),y2)   #,der=0)
                ioneqOne[goodt] = np.exp(gIoneq)
            else:
                gIoneq=interpolate.splev(np.log(self.Temperature),y2)
                ioneqOne = np.exp(gIoneq)
        else:
            ioneqOne = 0.
        #
        self.IoneqOne = ioneqOne
        #
        # -------------------------------------------------------------------------------------
        #
