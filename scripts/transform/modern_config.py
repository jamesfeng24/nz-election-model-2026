"""Explicit metadata for inspected modern Electoral Commission source families."""
from dataclasses import dataclass


@dataclass(frozen=True)
class ElectionConfig:
    year: int
    general_electorates: int
    maori_electorates: int
    source_files: int
    aggregate_affiliations: tuple = ()
    supporting_split_numbers: tuple = ()
    cancelled_contests: tuple = ()

    @property
    def total_electorates(self):
        return self.general_electorates + self.maori_electorates

    @property
    def election_id(self):
        return f'nz-general-{self.year}'

    @property
    def boundary_version_id(self):
        return f'historical-election-{self.year}-as-published'

    @property
    def source_plan(self):
        return f'data/source-plans/historical-{self.year}.json'


CONFIGS = {
    2017: ElectionConfig(2017, 64, 7, 145),
    2023: ElectionConfig(2023, 65, 7, 147, aggregate_affiliations=(('NZ Outdoors & Freedom Party', 'Freedoms NZ'), ('Rock the Vote NZ', 'Freedoms NZ'), ('Vision New Zealand', 'Freedoms NZ')), cancelled_contests=(('Port Waikato', 39),)),
    2020: ElectionConfig(2020, 65, 7, 148, (('NZ Public Party', 'Advance NZ'),), (70,)),
}


def election_config(year):
    try:
        return CONFIGS[year]
    except KeyError as error:
        raise ValueError(f'Unsupported modern election: {year}') from error
