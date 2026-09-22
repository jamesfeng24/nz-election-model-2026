"""Explicit interpretation of the pre-specified diagnostic conflicts."""
from scripts.models.party_vote_transform.formulas import METHODS


def interpret(reports):
    lookup={(r['scope'],r['evidence'],r['group']):r['scores'] for r in reports}
    primary={k:lookup[k,'primary_observed','all_persistent'] for k in ['general','maori']}
    robust={k:lookup[k,'all_five','all_persistent'] for k in ['general','maori']}
    winner=lambda scores:min(METHODS,key=lambda m:scores[m]['macroPartyMAE'][0])
    transition_winners={scope:{str(y):winner(lookup[scope,'transition',str(y)]) for y in [2008,2014,2020]} for scope in primary}
    conflicts=[]
    if len(set(transition_winners['maori'].values()))>1:conflicts.append('Māori observed-transition winners differ; proportional wins2008→2011 and2014→2017, log-odds wins2020→2023.')
    labour=lookup['general','primary_observed','party:labourparty']
    if winner(labour)!=winner(primary['general']):conflicts.append('General Labour favours additive MAE/RMSE while overall macro-party scores favour log-odds.')
    if not conflicts:raise ValueError('Selection interpretation requires review: expected diagnostic conflict changed')
    dominance={scope:{m:robust[scope]['log_odds']['macroPartyMAE'][1]<robust[scope][m]['macroPartyMAE'][0] for m in ['additive','proportional']} for scope in primary}
    return {'schemaVersion':1,'selectionStatus':'unresolved_between_methods','defaultLocalPartyVoteTransform':None,
        'retainedCandidateSet':list(METHODS),'leadingGenericEvidence':'log_odds',
        'primaryScores':primary,'allFiveMarginalRobustness':robust,'observedTransitionWinners':transition_winners,
        'logOddsRobustlyLowerMacroMAE':dominance,'conflicts':conflicts,
        'rationale':'Log-odds leads overall observed macro-party MAE and RMSE in both scopes and remains superior under conservative five-transition macro-MAE enclosures. However pre-specified scope/transition and National/Labour diagnostics materially conflict. Do not impose a universal default. Retain additive for general Labour, proportional for early Māori evidence, and log-odds as overall leader.',
        'nextStageRequirement':'NAT/LAB electorate elasticity must test conclusions across retained baseline transformations; no elasticity fitted here.',
        'limitations':['Only three primary election-transition clusters; seven Māori electorates each, no independent-electorate significance claim.',
                      'All-five losses are marginal conservative bounds, not jointly attained election-wide losses; no optimizer added.',
                      'Small-party thresholds0.5% and1% were frozen before scoring; all results are reported. No tuned exclusions.',
                      'No vector renormalization, future political data, Opportunity mapping or candidate effects.']}
