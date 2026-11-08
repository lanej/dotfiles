import re,sys
p='.golangci.yml'; s=open(p).read()
m=re.search(r'<<<<<<< [^\n]*\n(.*?)\|\|\|\|\|\|\| [^\n]*\n(.*?)=======\n(.*?)>>>>>>> [^\n]*\n',s,re.S)
if not m: sys.exit(2)
ours,base,theirs=m.groups()
def alt(block):
    mm=re.search(r'\^internal/\((.*)\)\s*$',block.strip().split('path-except:')[-1].strip())
    if not mm: raise SystemExit(3)
    # split top-level on | (no nested parens except (_test)?)
    parts=[];depth=0;cur=''
    for ch in mm.group(1):
        if ch=='(':depth+=1
        if ch==')':depth-=1
        if ch=='|' and depth==0: parts.append(cur);cur=''
        else: cur+=ch
    parts.append(cur); return parts
o,b,t=alt(ours),alt(base),alt(theirs)
new=[x for x in t if x not in b and x not in o]
rem=[x for x in b if x not in t]   # removed by theirs
merged=o+new  # additive only: never drop packages already enforced on main
indent=re.match(r'\s*',ours).group(0)
line=f"{indent}path-except: ^internal/({'|'.join(merged)})\n"
s=s[:m.start()]+line+s[m.end():]
open(p,'w').write(s); print('resolved: +',new,'-',rem)
