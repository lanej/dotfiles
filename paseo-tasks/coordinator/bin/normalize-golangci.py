import re,sys,os,subprocess
p='.golangci.yml'; s=open(p).read()
rx=r'^(\s*path-except: \^internal/)\((.*)\)\s*$'
def toks(text):
    m=re.search(rx,text,re.M)
    if not m: return None,None
    parts=[];depth=0;cur=''
    for ch in m.group(2):
        if ch=='(':depth+=1
        if ch==')':depth-=1
        if ch=='|' and depth==0: parts.append(cur);cur=''
        else: cur+=ch
    parts.append(cur); return m,parts
m,parts=toks(s)
if not m: sys.exit(0)
add=[x for x in os.environ.get('SCOPE_ADD','').split(',') if x]
if os.environ.get('SCOPE_ADD') is not None:
    main=subprocess.run(['git','show','origin/main:.golangci.yml'],capture_output=True,text=True).stdout
    _,mp=toks(main); parts=mp+add
seen=[];[seen.append(x) for x in parts if x and x not in seen]
new=f"{m.group(1)}({'|'.join(seen)})"
if new!=m.group(0).rstrip('\n'):
    s=s[:m.start()]+new+s[m.end():]; open(p,'w').write(s); print('normalized')
