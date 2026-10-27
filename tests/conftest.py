import numpy as np
from mocap_qc.models import MarkerTake, SkeletonTake


def trajectory(times):
    t=np.asarray(times)
    return np.column_stack((.45*np.sin(1.3*t)+.07*np.sin(5.1*t),
                            .3*np.cos(.8*t)+.06*np.cos(3.4*t),
                            1+.06*np.sin(2.3*t)))


def make_markers(frames=360, count=6, rate=120):
    t=np.arange(frames)/rate
    p=trajectory(t)[:,None,:]+np.array([[.04*j,.02*(j%2),.01*(j%3)] for j in range(count)])[None,:,:]
    return MarkerTake(tuple(f'A1:P{j}' for j in range(count)),p,np.ones((frames,count),bool),rate)


def make_skeleton(frames=360, rate=120):
    t=np.arange(frames)/rate
    root=trajectory(t)
    offsets=np.array([[0,0,0],[0,.3,0],[.2,.3,0]])
    p=root[:,None]+offsets
    local=np.empty_like(p); local[:,0]=root; local[:,1]=[0,.3,0]; local[:,2]=[.2,0,0]
    q=np.zeros((frames,3,4)); q[:,:,3]=1
    return SkeletonTake(('Hips','Hips/Arm','Hips/Arm/Hand'),np.array([-1,0,1]),t,p,local,q,np.ones_like(p))
