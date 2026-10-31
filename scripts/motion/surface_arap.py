"""Small geometric ARAP authoring solver shared by contact prototypes."""
import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.sparse.linalg import splu

class SurfaceArap:
 def __init__(self,p,faces,C,fixed,strength=1000.):
  self.p=p;self.C=C;self.strength=strength;edges=np.unique(np.sort(np.vstack([faces[:,[0,1]],faces[:,[1,2]],faces[:,[2,0]]]),axis=1),axis=0);self.a,self.b=edges.T;self.v=p[self.a]-p[self.b];degree=np.bincount(edges.ravel(),minlength=len(p));a,b=self.a,self.b
  L=coo_matrix((np.r_[degree,-np.ones(2*len(edges))],(np.r_[np.arange(len(p)),a,b],np.r_[np.arange(len(p)),b,a])),shape=(len(p),len(p))).tocsc();count,labels=connected_components(L,directed=False);fixed=set(map(int,fixed))
  for comp in range(count):
   ids=np.flatnonzero(labels==comp)
   if not fixed.intersection(ids):fixed.add(int(ids[0]))
  self.fixed=np.array(sorted(fixed));self.free=np.array(sorted(set(range(len(p)))-fixed));self.Cf=C[:,self.free];self.Cc=C[:,self.fixed];self.Lfc=L[self.free][:,self.fixed];self.solver=splu((L[self.free][:,self.free]+strength*(self.Cf.T@self.Cf)).tocsc())
 def solve(self,q,target,fixedvalues=None,iterations=12):
  p=self.p;a,b=self.a,self.b;v=self.v;fixedvalues=p[self.fixed]if fixedvalues is None else fixedvalues;contact=self.strength*(self.Cf.T@(target-self.Cc@fixedvalues));boundary=self.Lfc@fixedvalues
  for _ in range(iterations):
   e=q[a]-q[b];outer=e[:,:,None]*v[:,None,:];S=np.zeros((len(p),3,3));np.add.at(S,a,outer);np.add.at(S,b,outer);U,_,Vt=np.linalg.svd(S);sign=np.linalg.det(U@Vt);U[:,:,2]*=np.where(sign<0,-1,1)[:,None];R=U@Vt;term=np.einsum('nij,nj->ni',(R[a]+R[b])*.5,v);rhs=np.zeros_like(p);np.add.at(rhs,a,term);np.add.at(rhs,b,-term);q[self.fixed]=fixedvalues;q[self.free]=self.solver.solve(rhs[self.free]-boundary+contact)
  return q
