import re,glob,json,itertools
res={'Deprecated':{},'Removed':{},'file':{}}
files=sorted(glob.glob('/tmp/src/sbwiki/releasenotes/Spring-Boot-[234].*-Configuration-Changelog.asciidoc'))+['/tmp/src/sbwiki/Spring-Boot-4.1.0-Configuration-Changelog.asciidoc']
for f in files:
    s=open(f,encoding='utf-8').read()
    for m in re.finditer(r'^== (Deprecated|Removed) in `?([0-9][^`\n]*?)`?\s*$',s,re.M):
        kind,ver=m.groups()
        rest=s[m.end():]
        t=re.search(r'^\|=+\s*$(.*?)^\|=+\s*$',rest,re.S|re.M)
        body=t.group(1)
        cells=[c.strip() for c in body.split('|')[1:]]
        hdr=cells[:3]; cells=cells[3:]
        ncol=3
        rows=[list(b) for b in itertools.batched(cells,ncol) if len(b)==ncol]
        res[kind].setdefault(ver,[]).extend(rows)
        res['file'][ver]=f
json.dump(res,open(__import__('os').path.join(__import__('os').path.dirname(__file__),'data','sb-config-changelog.json'),'w',encoding='utf-8'),indent=0)
tot=0
for v,rows in res['Deprecated'].items():
    rep=[r for r in rows if r[1].strip('`')]
    tot+=len(rep)
    print(v,len(rows),len(rep), rep[:1])
print(tot,{v:len(r) for v,r in res['Removed'].items()})
