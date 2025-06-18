# Singal Study
We have to perform mass fitting based on this approach
* 1D mass fitting: One dimension fitting can be perform either on diphoton mass, dibjet mass, or reduced mass. (p.s.  Fitting reduced mass should be a task
* 2D mass fitting: two dimensions fitting, taking two mass at a time. It could be diphoton & dibjet, diphoton & reduced mass, or dibjet & reduced mass.
* 3D mass fitting: most challenging one including all of the masses.

fitting fucntions are:
- [ ] Bernstein polynomials
- [ ] Exponential functions
- [ ] Power law functions
- [ ] Landau distributions
- [ ] Kolmogorov distribution(https://en.wikipedia.org/wiki/Kolmogorov–Smirnov_test#Kolmogorov_distribution)
- [ ] Binned Likelihoods with Templates
- [ ] Johnson Distributions
- [ ] Spline Functions
- [ ]  Double-Sided Crystal Ball Function
- [ ] Generalized Hyperbolic Functions
- [ ] RooFit-specific PDFs
- [ ] Voigt Profile
- [ ] Laurent Series
- [ ] Chebyshev Polynomials

from Lata's paper, 
- For signal modeling, categorized events are fitted with a product of two parametric 
    - signal models: a sum of Gaussian distributions for mγ γ and a double-sided Crystal Ball (CB) function or the sum of a CB and a Gaussian function for mjj. The mγ γ distribution is parametrized using the sum of up to five Gaussian functions without any constraint to have a common mean.
    
 -  for the ggF H and VBF H:
     - the mjj distribution is modeled with a Bernstein polynomial; for VH production, a CB function is used to model the distribution of the hadronic decays of vector bosons;
for ttH, where the two b jets are produced from a top quark decay, a Gaussian function
with a mean value of 120GeV is used. These backgrounds are negligible for mX >550 GeV,
therefore, they are absorbed within the nonresonant background model coming from data
to simplify the signal extraction procedure.
The nonresonant background model is extracted from data using the discrete profiling
method described in refs. [68, 81]. This method makes use of polynomial and exponential
functions to decide the analytic functions to fit the background mγ γ and mjj distributions. It
estimates the systematic uncertainty associated with these functions and treats the choice of
background function as a discrete nuisance parameter in the likelihood fit to the data. For
background modeling, the fit functions are optimized on data where the events from the signal
region with 115 < mγ γ < 135 GeV are not taken into account.