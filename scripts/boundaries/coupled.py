"""Deterministic LP bounds for globally coupled population allocations.

Variables are group-to-target flows. Each source group retains its own total
interval and target totals are exact. No solver witness is a population estimate.
"""
from fractions import Fraction
import numpy as np
from scipy.optimize import linprog


class PopulationSystem:
    def __init__(self, groups, controls):
        self.groups, self.controls = groups, controls
        self.variables = [(g['id'], g['source'], target) for g in groups for target in g['targets']]
        if len(set(self.variables)) != len(self.variables) or len({g['id'] for g in groups}) != len(groups):
            raise ValueError('Duplicate population variable/group')
        if {v[2] for v in self.variables} != set(controls):
            raise ValueError('Incomplete target controls')
        self.n = len(self.variables)
        self.A, self.b = [], []
        for g in groups:
            if not 0 <= g['lower'] <= g['upper']:
                raise ValueError('Invalid group bounds')
            row = np.array([float(v[0] == g['id']) for v in self.variables])
            self.A.extend([row, -row]); self.b.extend([g['upper'], -g['lower']])
        self.A, self.b = np.array(self.A), np.array(self.b)
        self.E = np.array([[float(v[2] == t) for v in self.variables] for t in sorted(controls)])
        self.c = np.array([controls[t] for t in sorted(controls)],dtype=float)
        self.solve(np.zeros(self.n))

    def vector(self, source=None, target=None):
        return np.array([float((source is None or s == source) and (target is None or t == target))
                         for _,s,t in self.variables])

    def verify(self, x, tolerance=1e-6):
        if len(x) != self.n or not np.all(np.isfinite(x)) or min(x) < -tolerance:
            raise ValueError('Invalid population witness')
        if max(np.sum(self.A*x,axis=1) - self.b) > tolerance or max(abs(np.sum(self.E*x,axis=1) - self.c)) > tolerance:
            raise ValueError('Population witness violates global constraints')

    def solve(self, objective, maximize=False):
        result = linprog(-objective if maximize else objective, A_ub=self.A, b_ub=self.b,
                         A_eq=self.E, b_eq=self.c, bounds=(0,None), method='highs-ds',
                         options={'primal_feasibility_tolerance':1e-9,'dual_feasibility_tolerance':1e-9})
        if not result.success:
            raise ValueError('Infeasible/unresolved population system: '+result.message)
        # This group→destination network has integer capacities and a totally
        # unimodular matrix. Certify its integral optimal vertex, not a midpoint.
        x = np.rint(result.x)
        if max(abs(x-result.x)) > 1e-5:
            raise ValueError('Unexpected nonintegral network optimum')
        self.verify(x, tolerance=0)
        return x

    def bounds(self, objective):
        return tuple(int(round(np.sum(objective*self.solve(objective,maximize)))) for maximize in (False,True))

    def ratio(self, numerator, denominator, maximize=False):
        if self.bounds(denominator)[0] <= 0:
            raise ValueError('Source population can vanish; transfer weight undefined')
        r = Fraction(0)
        for _ in range(100):
            x = self.solve(numerator-float(r)*denominator,maximize)
            a,b = int(round(np.sum(numerator*x))),int(round(np.sum(denominator*x)))
            updated = Fraction(a,b)
            if updated == r:
                return r
            r = updated
        raise ValueError('Fractional LP did not converge')

    def edge_inventory(self):
        return sorted({(s,t) for _,s,t in self.variables})
