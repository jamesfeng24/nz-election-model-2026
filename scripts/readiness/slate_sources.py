"""Extract dated party assertions, never infer official nominations or full slates."""
from dataclasses import dataclass, field
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
import re


VOID_TAGS = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
             'link', 'meta', 'param', 'source', 'track', 'wbr'}
HIDDEN_TAGS = {'script', 'style', 'svg', 'head', 'noscript'}


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: object = None

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk()

    def text(self):
        if self.tag in HIDDEN_TAGS:
            return ''
        parts = [c.text() if isinstance(c, Node) else c for c in self.children]
        return ' '.join(' '.join(parts).split())

    def has_class(self, name):
        return name in self.attrs.get('class', '').split()


class Document(HTMLParser):
    """Minimal static DOM reader; scripts and duplicate hydration text stay hidden."""
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Node('document')
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID_TAGS:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.stack[-1].children.append(Node(tag, dict(attrs), parent=self.stack[-1]))

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        if not any(node.tag in HIDDEN_TAGS for node in self.stack):
            self.stack[-1].children.append(data)


def matching(node, *, tag=None, class_name=None):
    return [n for n in node.walk() if (tag is None or n.tag == tag)
            and (class_name is None or n.has_class(class_name))]


def first_text(node, *, tag=None, class_name=None):
    found = matching(node, tag=tag, class_name=class_name)
    return found[0].text() if found else None


def claim(source, name, seat, affiliation, passage, locator, *, status='party_announced',
          date=None, qualification=None):
    return {'sourceKey': source, 'displayName': name,
            'sourceElectorateLabel': seat, 'affiliationKey': affiliation,
            'status': status, 'factDate': date, 'publicationDate': date,
            'passage': passage, 'locator': locator,
            'qualification': qualification or 'Party assertion; not an official nomination.'}


def gap(source, reason, **details):
    return {'sourceKey': source, 'reason': reason, **details}


def card_claims(root, source, affiliation, card_class, name_class, seat_class):
    claims, context, gaps = [], [], []
    for index, card in enumerate(matching(root, tag='article', class_name=card_class)):
        name = first_text(card, class_name=name_class)
        seat = first_text(card, class_name=seat_class)
        locator = f'article.{card_class}[{index + 1}]'
        if not name:
            gaps.append(gap(source, 'candidate_card_missing_name', locator=locator))
        elif not seat:
            context.append(claim(source, name, None, affiliation, card.text(), locator,
                                 status='list_or_unspecified_electorate_context'))
        else:
            claims.append(claim(source, name, seat, affiliation, card.text(), locator))
    return claims, context, gaps


def national(root):
    source = 'national-team'
    nodes = list(root.walk())
    headings = [i for i, node in enumerate(nodes)
                if node.tag in {'h1', 'h2', 'h3'} and node.text() == 'Candidates for 2026']
    if len(headings) != 1:
        return [], [], [gap(source, 'missing_or_ambiguous_2026_section')]
    claims, context, gaps = [], [], []
    for index, node in enumerate(nodes):
        if node.tag != 'a':
            continue
        name = first_text(node, tag='h3')
        role = first_text(node, tag='p')
        if not name or not role:
            continue
        if index > headings[0] and role.startswith('Candidate for '):
            claims.append(claim(source, name, role.removeprefix('Candidate for '),
                                'nationalparty', f'{name} {role}',
                                node.attrs.get('href', f'a[{index}]')))
        elif index < headings[0]:
            context.append(claim(source, name, None, 'nationalparty', f'{name} {role}',
                                 node.attrs.get('href', f'a[{index}]'),
                                 status='incumbent_context_not_2026_candidacy'))
        else:
            gaps.append(gap(source, 'unrecognised_2026_card_role', displayName=name, role=role))
    return claims, context, gaps


def nzfirst(root):
    claims, context, gaps = [], [], []
    for index, card in enumerate(matching(root, tag='article', class_name='card-team')):
        name, role = first_text(card, tag='h3'), first_text(card, tag='h4')
        locator = f'article.card-team[{index + 1}]'
        if not name or not role:
            gaps.append(gap('nzfirst-team', 'candidate_card_missing_name_or_role', locator=locator))
        elif role.startswith('Candidate for '):
            claims.append(claim('nzfirst-team', name, role.removeprefix('Candidate for '),
                                'newzealandfirstparty', f'{name} {role}', locator))
        else:
            context.append(claim('nzfirst-team', name, None, 'newzealandfirstparty',
                                 f'{name} {role}', locator, status='incumbent_or_list_context'))
    return claims, context, gaps


def act(root):
    claims, context, gaps = [], [], []
    nodes = [n for n in root.walk() if n.tag in {'h1', 'h2', 'h3', 'p'}]
    section = 'main'
    for index, node in enumerate(nodes):
        text = node.text()
        if text in {'Electorate Only & Retiring MPs', 'Local Government Representatives', 'Unranked List'}:
            section = text
            continue
        if node.tag != 'h3' or section == 'Local Government Representatives':
            continue
        ancestor = node.parent
        while ancestor and not (ancestor.tag == 'a' and ancestor.attrs.get('href')):
            ancestor = ancestor.parent
        if ancestor is None:
            continue
        following = []
        for next_node in nodes[index + 1:]:
            if next_node.tag in {'h1', 'h2', 'h3'}:
                break
            following.append(next_node.text())
        if not following:
            gaps.append(gap('act-people', 'candidate_card_missing_role', displayName=text))
            continue
        role = following[0]
        locator = f'h3[{index + 1}]'
        passage = ' '.join([text, *following])
        ambiguous = section == 'Electorate Only & Retiring MPs'
        if ambiguous or role == 'List Candidate' or role.startswith('MP for '):
            reason = 'mixed_retiring_or_electorate_only_context' if ambiguous else 'list_or_incumbent_context'
            context.append(claim('act-people', text, None, 'actnewzealand', passage,
                                 locator, status=reason))
            if ambiguous:
                gaps.append(gap('act-people', reason, displayName=text, reportedRole=role))
        else:
            claims.append(claim('act-people', text, role, 'actnewzealand', passage, locator,
                                qualification='Current party directory seat assertion; generic headline, '
                                'not dated selection confirmation or official nomination.'))
    return claims, context, gaps


def publication_date(root):
    for node in root.walk():
        if node.tag == 'time' and node.attrs.get('datetime'):
            return node.attrs['datetime'][:10]
    text = root.text()
    found = re.search(r'Published by\s+Te Pāti Māori\s+([A-Z][a-z]+ \d{1,2}, \d{4})', text)
    return datetime.strptime(found[1], '%B %d, %Y').date().isoformat() if found else None


def maori(root, source):
    expected = {
        'maori-haley': ('Haley Maxwell', 'Ikaroa-Rāwhiti', 'Te Pāti Māori is proud to announce the nomination of Haley Maxwell'),
        'maori-lisa': ('Lisa Marie Murch', 'Te Tai Tonga', 'Te Pāti Māori is proud to announce Lisa Marie Murch'),
    }
    name, seat, prefix = expected[source]
    passages = [n.text() for n in matching(root, tag='p') if n.text().startswith(prefix)]
    if len(passages) != 1 or '2026' not in passages[0] or seat not in passages[0]:
        return [], [], [gap(source, 'selection_passage_missing_or_conflicting')]
    status = 'party_selected' if source == 'maori-haley' else 'party_announced'
    return [claim(source, name, seat, 'tepatimaori', passages[0], 'article body confirmation paragraph',
                  status=status, date=publication_date(root))], [], []


def willis(root):
    prefix = 'Deputy Leader of the National Party, Nicola Willis has today been confirmed as a List-Only candidate'
    passages = [n.text() for n in matching(root, tag='p') if n.text().startswith(prefix)]
    if len(passages) != 1 or '22 December 2025' not in root.text():
        return [], [], [gap('national-willis', 'list_only_confirmation_or_date_missing')]
    item = claim('national-willis', 'Nicola Willis', None, 'nationalparty', passages[0],
                 'article body confirmation paragraph', status='confirmed_list_only_no_target_seat',
                 date='2025-12-22')
    return [], [item], []


def extract_claims(raw_root):
    """Read only the finite preserved sources and expose missing/ambiguous cards."""
    raw_root = Path(raw_root)
    parsers = {
        'national-team': national, 'nzfirst-team': nzfirst, 'act-people': act,
        'green-candidates': lambda root: card_claims(root, 'green-candidates', 'greenparty',
                                'excerpt--people', 'excerpt--people__name', 'excerpt--people__role'),
        'opportunity-team': lambda root: card_claims(root, 'opportunity-team', 'opportunity',
                                'candidate-tile', 'candidate-tile__name', 'candidate-tile__region'),
        'maori-haley': lambda root: maori(root, 'maori-haley'),
        'maori-lisa': lambda root: maori(root, 'maori-lisa'), 'national-willis': willis,
    }
    result = {'claims': [], 'context': [], 'gaps': [], 'sourceCounts': {}}
    for source, parser in parsers.items():
        path = raw_root / f'{source}.html'
        if not path.exists():
            result['gaps'].append(gap(source, 'preserved_resource_missing'))
            continue
        claims, context, gaps = parser(Document(path.read_text(encoding='utf-8')).root)
        result['claims'].extend(claims)
        result['context'].extend(context)
        result['gaps'].extend(gaps)
        result['sourceCounts'][source] = {'claims': len(claims), 'context': len(context), 'gaps': len(gaps)}
    result['gaps'].append(gap('labour-candidates',
                             'directory_has_no_static_candidate_cards; party list alone does not establish electorate candidacy'))
    return result
