"""Joint observed candidate-vector feasibility on the frozen ballot ledger."""

from collections import defaultdict

import numpy as np
from scipy.optimize import linprog
from scipy.sparse import coo_matrix

from scripts.models.conditional_candidate_ledger.geometry import BALLOT_TOL, PROB_TOL


class FeasibilityProblem:
    def __init__(self):
        self.bounds = []
        self.equalities = []
        self.inequalities = []

    def variable(self, lower=0, upper=None):
        index = len(self.bounds)
        self.bounds.append((lower, upper))
        return index

    def equality(self, terms, right, unit):
        self.equalities.append((dict(terms), right, unit))

    def inequality(self, terms, right, unit):
        self.inequalities.append((dict(terms), right, unit))


def _matrix(constraints, count):
    rows, columns, values = [], [], []
    for row_index, (terms, _, _) in enumerate(constraints):
        for column, coefficient in terms.items():
            if coefficient:
                rows.append(row_index)
                columns.append(column)
                values.append(coefficient)
    matrix = coo_matrix((values, (rows, columns)),
                        shape=(len(constraints), count)).tocsr()
    return matrix, np.asarray([right for _, right, _ in constraints])


def _add_free(problem, candidate_terms, candidate_ids, mass_terms, mass_constant=0):
    """Allocate one free bucket jointly to candidates and an other destination."""
    destinations = [problem.variable() for _ in candidate_ids]
    other = problem.variable()
    for candidate, variable in zip(candidate_ids, destinations):
        candidate_terms[candidate][variable] += 1
    equation = {variable: 1 for variable in destinations + [other]}
    for variable, coefficient in mass_terms.items():
        equation[variable] = equation.get(variable, 0) - coefficient
    problem.equality(equation, mass_constant, 'ballots')


def _source_category_bounds(row):
    bounds = defaultdict(lambda: [0.0, 0.0])
    for cell in row['cells']:
        result = bounds[cell['category']]
        result[0] += cell['bounds'][0]
        result[1] += cell['bounds'][1]
    return dict(sorted(bounds.items()))


def _constrained_origin(problem, origin, source_pool, candidate_terms, candidate_ids):
    mass = origin['mass']
    rows = source_pool['rows']
    primary = origin['routing'] == 'primary'
    weights = []
    if not primary:
        weights = [problem.variable(0, 1) for _ in rows]
        problem.equality({variable: 1 for variable in weights}, 1, 'probability')
    absent_terms = defaultdict(float)
    mapping = origin['mappedSourceCategories']
    for row_index, row in enumerate(rows):
        categories = _source_category_bounds(row)
        variables = {}
        for category, (lower, upper) in categories.items():
            if primary:
                variable = problem.variable(lower, upper)
            else:
                variable = problem.variable(0, 1)
                scale = weights[row_index]
                problem.inequality({variable: 1, scale: -upper}, 0, 'probability')
                problem.inequality({variable: -1, scale: lower}, 0, 'probability')
            variables[category] = variable
        equation = {variable: 1 for variable in variables.values()}
        if not primary:
            equation[weights[row_index]] = -1
        problem.equality(equation, 1 if primary else 0, 'probability')
        factor = mass * (row['mass'] / source_pool['totalMass'] if primary else 1)
        for category, variable in variables.items():
            destination = mapping.get(category)
            if destination in candidate_terms:
                candidate_terms[destination][variable] += factor
            elif destination is None:
                absent_terms[variable] += factor
    if absent_terms:
        _add_free(problem, candidate_terms, candidate_ids, absent_terms)


def build_problem(method_record, source_pools, actual_votes):
    candidate_ids = [candidate['candidateOccurrenceId']
                     for candidate in method_record['candidates']]
    if set(candidate_ids) != set(actual_votes) or len(candidate_ids) != len(actual_votes):
        raise ValueError('Actual candidate vector differs from constructed destinations')
    problem = FeasibilityProblem()
    candidate_terms = {candidate: defaultdict(float) for candidate in candidate_ids}
    fixed = defaultdict(float)
    for origin in method_record['origins']:
        mass = origin['mass']
        if mass == 0:
            continue
        if origin['routing'] == 'free':
            _add_free(problem, candidate_terms, candidate_ids, {}, mass)
        elif origin['routing'] == 'diagonal':
            fixed[origin['destination']] += mass
        elif origin['routing'] in ('primary', 'heterogeneity'):
            _constrained_origin(problem, origin,
                                source_pools[origin['sourcePoolId']],
                                candidate_terms, candidate_ids)
        else:
            raise ValueError('Unknown source route in observed-vector problem')
    for candidate in candidate_ids:
        problem.equality(candidate_terms[candidate],
                         actual_votes[candidate] - fixed[candidate], 'ballots')
    return problem


def solve_problem(problem, solver=linprog):
    count = len(problem.bounds)
    if not count:
        raise ValueError('Empty observed-vector problem')
    equalities, equal_right = _matrix(problem.equalities, count)
    inequalities, upper_right = _matrix(problem.inequalities, count)
    result = solver(np.zeros(count), A_eq=equalities, b_eq=equal_right,
                    A_ub=inequalities if problem.inequalities else None,
                    b_ub=upper_right if problem.inequalities else None,
                    bounds=problem.bounds, method='highs',
                    options={'primal_feasibility_tolerance': 1e-9,
                             'dual_feasibility_tolerance': 1e-9})
    if result.status == 2:
        return {'status': 'infeasible', 'solverStatus': 2}
    if result.status != 0 or result.x is None:
        return {'status': 'numerical_or_solver_failure',
                'solverStatus': int(result.status)}
    eq_residual = np.abs(equalities @ result.x - equal_right)
    upper_residual = (inequalities @ result.x - upper_right
                      if problem.inequalities else np.array([]))
    probability = max((float(value) for value, row in zip(eq_residual,
                      problem.equalities) if row[2] == 'probability'), default=0.0)
    probability = max(probability, max((float(value) for value, row in zip(
                      upper_residual, problem.inequalities)
                      if row[2] == 'probability'), default=0.0))
    ballot = max((float(value) for value, row in zip(eq_residual,
                  problem.equalities) if row[2] == 'ballots'), default=0.0)
    lower = max((lower - value for value, (lower, _) in zip(result.x, problem.bounds)),
                default=0.0)
    upper = max((value - bound for value, (_, bound) in zip(result.x, problem.bounds)
                 if bound is not None), default=0.0)
    if probability > PROB_TOL or ballot > BALLOT_TOL or lower > PROB_TOL or upper > PROB_TOL:
        return {'status': 'numerical_or_solver_failure', 'solverStatus': 0,
                'probabilityResidual': probability, 'ballotResidual': ballot,
                'boundViolation': max(lower, upper)}
    return {'status': 'feasible', 'solverStatus': 0,
            'probabilityResidual': probability, 'ballotResidual': ballot,
            'boundViolation': max(0.0, lower, upper), 'variables': count,
            'equalities': len(problem.equalities),
            'inequalities': len(problem.inequalities)}


def joint_feasibility(method_record, source_pools, actual_votes, solver=linprog):
    """Check all actual candidate totals together, never as independent bounds."""
    origins = method_record['origins']
    if all(origin['routing'] in ('free', 'diagonal') for origin in origins):
        fixed = defaultdict(float)
        free = 0
        for origin in origins:
            if origin['routing'] == 'free':
                free += origin['mass']
            else:
                fixed[origin['destination']] += origin['mass']
        remaining = [votes - fixed[candidate] for candidate, votes in actual_votes.items()]
        feasible = (min(remaining, default=0) >= -BALLOT_TOL and
                    sum(remaining) <= free + BALLOT_TOL)
        return {'status': 'feasible' if feasible else 'infeasible',
                'strategy': 'exact_free_mass_arithmetic'}
    return solve_problem(build_problem(method_record, source_pools, actual_votes), solver)
