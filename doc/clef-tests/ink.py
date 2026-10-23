from pathlib import Path
import json,math,re,xml.etree.ElementTree as E
here=Path(__file__).resolve().parent
I=(1.,0.,0.,1.,0.,0.)
def mul(x,y):
 a,b,c,d,e,f=x;A,B,C,D,F,G=y
 return(a*A+c*B,b*A+d*B,a*C+c*D,b*C+d*D,a*F+c*G+e,b*F+d*G+f)
def transform(s):
 m=I
 for op,args in re.findall(r'(\w+)\(([^)]*)\)',s or ''):
  v=list(map(float,re.findall(r'[-+]?(?:\d*\.\d+|\d+\.?\d*)(?:[eE][-+]?\d+)?',args)))
  if op=='matrix':t=tuple(v)
  elif op=='translate':t=(1,0,0,1,v[0],v[1] if len(v)>1 else 0)
  elif op=='scale':t=(v[0],0,0,v[1] if len(v)>1 else v[0],0,0)
  elif op=='rotate':
   a=math.radians(v[0]);t=(math.cos(a),math.sin(a),-math.sin(a),math.cos(a),0,0)
   if len(v)==3:t=mul(mul((1,0,0,1,v[1],v[2]),t),(1,0,0,1,-v[1],-v[2]))
  else:raise AssertionError(op)
  m=mul(m,t)
 return m
def local(e):return e.tag.rsplit('}',1)[-1]
DEFAULT={'color':'black','fill':'black','fill-rule':'nonzero','fill-opacity':'1','stroke':'none','stroke-width':'1','stroke-opacity':'1','stroke-linecap':'butt','stroke-linejoin':'miter','stroke-miterlimit':'4','stroke-dasharray':'none','stroke-dashoffset':'0','opacity':'1'}
def paint(e,inherited):
 p=dict(inherited);a=dict(e.attrib)
 for entry in e.get('style','').split(';'):
  if ':' in entry:k,v=entry.split(':',1);a[k.strip()]=v.strip()
 for k in DEFAULT:
  if k!='opacity' and a.get(k,'inherit')!='inherit':p[k]=a[k]
 p['opacity']=str(float(inherited['opacity'])*float(a.get('opacity','1')))
 return p
def paths(e,ids,m,p):
 if e.get('visibility')=='hidden' or e.get('display')=='none':return []
 m=mul(m,transform(e.get('transform')));p=paint(e,p)
 if local(e)=='use':
  m=mul(m,(1,0,0,1,float(e.get('x','0')),float(e.get('y','0'))))
  return paths(ids[(e.get('href') or e.get('{http://www.w3.org/1999/xlink}href'))[1:]],ids,m,p)
 if local(e)=='path':
  q={k:(p['color'] if v=='currentColor' else v) for k,v in p.items()}
  for k in ['fill-opacity','stroke-opacity','opacity','stroke-width','stroke-miterlimit','stroke-dashoffset']:q[k]=float(q[k])
  return [(e.get('d'),m,q)] if e.get('d') else []
 return [x for c in e for x in paths(c,ids,m,p)]
def load(path):
 r=E.parse(path).getroot();return r,{e.get('id'):e for e in r.iter() if e.get('id')},{c:e for e in r.iter() for c in e}
def normalize(ps):
 assert ps,'actual nonempty ink required'
 x=ps[0][1][4]
 return [(d,(*m[:4],m[4]-x,m[5]),p) for d,m,p in ps]
def original(path,which):
 r,ids,parents=load(path)
 candidates=[e for e in r.iter() if 'clef' in e.get('class','').split() and paths(e,ids,I,DEFAULT)]
 e=next(e for e in candidates if e.get('id')==which) if isinstance(which,str) else candidates[which]
 staff=parents[e]
 while 'staff' not in staff.get('class','').split():staff=parents[staff]
 ys=[float(re.findall(r'[-+]?\d*\.?\d+',x.get('d'))[1]) for x in staff if local(x)=='path']
 top=ys[0];space=abs(ys[1]-top)
 chain=[];parent=parents.get(e)
 while parent is not None:chain.append(parent);parent=parents.get(parent)
 p=DEFAULT
 for parent in reversed(chain):p=paint(parent,p)
 return normalize(paths(e,ids,(1/space,0,0,1/space,0,-top/space),p))
def recovered(path):
 r,ids,_=load(path);return normalize(paths(r,ids,I,DEFAULT))
