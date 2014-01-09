"""
Extra distributions to complement scipy.stats

"""
import numpy as np
import numpy.random as mtrand
import scipy.stats
from scipy.stats import rv_continuous, rv_discrete
from scipy.stats.distributions import rv_generic


class loguniform_gen(rv_continuous):
    """ Stats for Y = e^X where X ~ U(low, high).

    """
    def __init__(self, low=0, high=1):
        rv_continuous.__init__(self,
                a=np.exp(low),
                b=np.exp(high))
        self._low = low
        self._high = high

    def _rvs(self):
        rval = np.exp(mtrand.uniform(
            self._low,
            self._high,
            self._size))
        return rval

    def _pdf(self, x):
        return 1.0 / (x * (self._high - self._low))

    def _logpdf(self, x):
        return - np.log(x) - np.log(self._high - self._low)

    def _cdf(self, x):
        return (np.log(x) - self._low) / (self._high - self._low)


class quniform_gen(rv_discrete):
    """ Stats for Y = q * round(X / q) where X ~ U(low, high).

    """
    def __init__(self, low, high, q):
        low, high, q = map(float, (low, high, q))
        qlow = np.round(low / q) * q
        qhigh = np.round(high / q) * q
        self._args = {
                'low': low,
                'high': high,
                'q': q,
                }
        if qlow == qhigh:
            rv_discrete.__init__(self, name='quniform',
                                 values=([qlow], [1.0]))
        else:
            lowmass = 1 - ((low - qlow + .5 * q) / q)
            assert 0 <= lowmass <= 1.0, (lowmass, low, qlow, q)
            highmass = (high - qhigh + .5 * q) / q
            assert 0 <= highmass <= 1.0, (highmass, high, qhigh, q)
            # -- xs: qlow to qhigh inclusive
            xs = np.arange(qlow, qhigh + .5 * q, q)
            ps = np.ones(len(xs))
            ps[0] = lowmass
            ps[-1] = highmass
            ps /= ps.sum()
            #print 'lowmass', lowmass, low, qlow, q
            #print 'highmass', highmass, high, qhigh, q
            rv_discrete.__init__(self, name='quniform',
                    values=(xs, ps))
        self._xs = np.asarray(xs)
        self._ps = ps

    def rvs(self, *args, **kwargs):
        # -- skip rv base class to avoid cast to integer
        return rv_generic.rvs(self, *args, **kwargs)

    def _rvs(self, *args):
        q, low, high = map(self._args.get, ['q', 'low', 'high'])
        rval = mtrand.uniform(low=low, high=high, size=self._size)
        rval = np.round(rval / q) * q
        # -- return nearest-matching elements of self._xs
        idxs = np.searchsorted(self._xs, rval - 1e-6, 'right')
        assert np.allclose(rval, self._xs[idxs])
        return self._xs[idxs]


class qloguniform_gen(rv_discrete):
    """ Stats for Y = q * round(e^X / q) where X ~ U(low, high).

    """

    def __init__(self, low, high, q):
        low, high, q = map(float, (low, high, q))
        self._args = {
                'low': low,
                'high': high,
                'q': q,
                }
        qlow = np.round(np.exp(low) / q) * q
        qhigh = np.round(np.exp(high) / q) * q

        # -- loguniform for using the CDF
        lu = loguniform_gen(low=low, high=high)

        xs = []
        ps = []
        cut_low = np.exp(low)
        cut_high = qlow + .5 * q
        val = qlow
        while cut_low < qhigh:
            xs.append(val)
            ps.append(lu.cdf(cut_high) - lu.cdf(cut_low))
            cut_high, cut_low = min(cut_high + q, np.exp(high)), cut_high
            val += q

        ps = np.asarray(ps)
        ps /= ps.sum()
        #print xs
        #print ps
        rv_discrete.__init__(self, name='qloguniform',
                             values=(xs, ps))
        self._xs = np.asarray(xs)
        self._ps = ps

    def rvs(self, *args, **kwargs):
        # -- skip rv base class to avoid cast to integer
        return rv_generic.rvs(self, *args, **kwargs)

    def _rvs(self, *args):
        q, low, high = map(self._args.get, ['q', 'low', 'high'])
        x = mtrand.uniform(low=low, high=high, size=self._size)
        rval = np.round(np.exp(x) / q) * q
        # -- return nearest-matching elements of self._xs
        idxs = np.searchsorted(self._xs, rval - 1e-6, 'right')
        assert np.allclose(rval, self._xs[idxs])
        return self._xs[idxs]


class qnormal_gen(rv_discrete):
    """Stats for Y = q * round(X / q) where X ~ N(mu, sigma)
    """
    def __init__(self, mu, sigma, q):
        low, high, q = map(float, (mu, sigma, q))
        self._args = {
                'mu': mu,
                'sigma': sigma,
                'q': q,
                }

        # -- distfn for using the CDF
        self._norm_cdf = scipy.stats.norm(loc=mu, scale=sigma).cdf
        BIG = 1e17
        rv_discrete.__init__(self,
                             a=-BIG,
                             b=BIG,
                             name='qnormal',
                             inc=q)

    def rvs(self, *args, **kwargs):
        # -- skip rv base class to avoid cast to integer
        return rv_generic.rvs(self, *args, **kwargs)

    def _ppf(self, x):
        raise NotImplementedError()

    def pmf(self, k, *args, **kwds):
        loc = kwds.get('loc')
        args, loc = self._fix_loc(args, loc)
        k,loc = map(np.asarray,(k,loc))
        args = tuple(map(np.asarray,args))
        k = np.asarray((k-loc))
        cond0 = self._argcheck(*args)
        cond1 = (k >= self.a) & (k <= self.b) #& self._nonzero(k,*args)
        cond = cond0 & cond1
        output = np.zeros(np.shape(cond),'d')
        np.place(output,(1-cond0) + np.isnan(k),self.badvalue)
        if np.any(cond):
            goodargs = scipy.stats.distributions.argsreduce(cond, *((k,)+args))
            np.place(output,cond,self._pmf(*goodargs))
        if output.ndim == 0:
            return output[()]
        return output

    def _pmf(self, x):
        return self._cdf(x) - self._cdf(x - self.inc)

    def _cdf(self, x):
        return self._norm_cdf(x + 0.5 * self.inc)


    def _rvs(self, *args):
        q, mu, sigma = map(self._args.get, ['q', 'mu', 'sigma'])
        x = mtrand.normal(loc=mu, scale=sigma, size=self._size)
        rval = np.round(x / q) * q
        return rval


class qlognormal_gen(rv_discrete):
    """Stats for Y = q * round(exp(X) / q) where X ~ N(mu, sigma)
    """
    def __init__(self, mu, sigma, q):
        low, high, q = map(float, (mu, sigma, q))
        self._args = {
                'mu': mu,
                'sigma': sigma,
                'q': q,
                }

        # -- distfn for using the CDF
        self._norm_cdf = scipy.stats.norm(loc=mu, scale=sigma).cdf
        BIG = 1e17
        rv_discrete.__init__(self,
                             a=0,
                             b=BIG,
                             name='qnormal',
                             inc=q)

    def rvs(self, *args, **kwargs):
        # -- skip rv base class to avoid cast to integer
        raise NotImplementedError()
        return rv_generic.rvs(self, *args, **kwargs)

    def _rvs(self, *args):
        q, mu, sigma = map(self._args.get, ['q', 'mu', 'sigma'])
        x = mtrand.normal(loc=mu, scale=sigma, size=self._size)
        rval = np.round(x / q) * q
        return rval


# -- non-empty last line for flake8