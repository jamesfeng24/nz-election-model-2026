"""Small independent adapter for the pinned2026 party table; no inferred releases."""
import re
from datetime import datetime
from html.parser import HTMLParser
from .records import record


class Tables(HTMLParser):
    def __init__(self):
        super().__init__();self.tables=[];self.depth=0;self.rows=[];self.row=[];self.cell=None

    def handle_starttag(self,tag,attrs):
        if tag=='table':
            self.depth+=1
            if self.depth==1:self.rows=[]
        if self.depth!=1:return
        if tag=='tr':self.row=[]
        if tag in ('td','th'):self.cell=[]

    def handle_data(self,text):
        if self.cell is not None:self.cell.append(text)

    def handle_endtag(self,tag):
        if self.depth==1:
            if tag in ('td','th') and self.cell is not None:
                self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
            if tag=='tr':self.rows.append(self.row)
            if tag=='table':self.tables.append(self.rows)
        if tag=='table':self.depth-=1


def clean(text):
    return re.sub(r'\[[^\]]*\]','',text).strip()


def dates(text):
    text=clean(text).replace('–','-').replace('—','-')
    m=re.fullmatch(r'(\d+)\s*-\s*(\d+) ([A-Za-z]+) (\d{4})',text)
    if m:
        a,b,month,year=m.groups()
        return [datetime.strptime(f'{d} {month[:3]} {year}','%d %b %Y').date().isoformat() for d in (a,b)]
    m=re.fullmatch(r'(\d+) ([A-Za-z]+)\s*-\s*(\d+) ([A-Za-z]+) (\d{4})',text)
    if m:
        a,ma,b,mb,y=m.groups()
        return [datetime.strptime(f'{d} {mo[:3]} {y}','%d %b %Y').date().isoformat() for d,mo in ((a,ma),(b,mb))]
    return [datetime.strptime(text,'%d %b %Y').date().isoformat()]


def pollster(text):
    for pattern,code in [('Verian|Kantar|Colmar','COL'),('Reid','REI'),('Curia','CUR'),
      ('Roy Morgan','ROY'),('Talbot|UMR','TBM'),('Freshwater','FWS'),('Anacta','ANA'),
      ('Essential','ESS'),('Horizon','HOR'),('YouGov','YGV')]:
        if re.search(pattern,text):return code
    raise ValueError('Unrecognized pollster')


def parse_current(html,source_id):
    parser=Tables();parser.feed(html)
    tables=[t for t in parser.tables if t and t[0][:3]==['Date[a]','Polling organisation','Sample size'] and 'NAT' in t[0]]
    if len(tables)!=1:raise ValueError('Party table layout')
    table=tables[0];header=table[0];output=[];audit=[]
    for row_number,row in enumerate(table[1:],2):
        if len(row)!=len(header):
            audit.append({'row':row_number,'reason':'event_or_layout_row','raw':row});continue
        try:
            fs={'date':dates(row[0]),'org':pollster(row[1]),'n':clean(row[2])}
            for k,v in zip(header[3:-1],row[3:-1]):fs[{'TPM':'MRI','OPP':'TOP','Others':'OTH'}.get(k,k)]=clean(v)
            r=record(2026,fs,{'sourceId':source_id,'row':row_number,'sourceType':'aggregator'})
            r['commissioner']=row[1];output.append(r)
        except ValueError as exc:audit.append({'row':row_number,'reason':str(exc),'raw':row})
    return output,audit
