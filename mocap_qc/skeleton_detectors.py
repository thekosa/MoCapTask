"""Joint-local rotations and bone lengths avoid duplicate alarms on descendants."""
import numpy as np
from .models import Event
from .numerics import angular_steps, robust_limit, runs
from .marker_detectors import positional_spikes


def detect_skeleton(take):
    events=[]
    for j,n in enumerate(take.names):
        valid=(np.isfinite(take.positions[:,j]).all(axis=1) & np.isfinite(take.rotations[:,j]).all(axis=1)
               & (np.linalg.norm(take.rotations[:,j],axis=1)>1e-8))
        for a,b in runs(~valid):
            events.append(Event('invalid_joint',(n,),a,b,1.0,'Non-finite joint data or a degenerate rotation.'))
    roots=np.flatnonzero(take.parents<0)
    events+=positional_spikes(take.positions[:,roots],tuple(take.names[i] for i in roots),take.rate,
                             event_type='skeleton_translation_spike')
    angles=angular_steps(take.rotations)
    for j,n in enumerate(take.names):
        limit=robust_limit(angles[:,j],35.0,20)
        transitions=list(np.flatnonzero(angles[:,j]>limit)+1)
        i=0
        while i<len(transitions):
            a=int(transitions[i]); b=a; kind='rotation_jump'
            if i+1<len(transitions):
                end=int(transitions[i+1])
                q0=take.rotations[a-1,j]; q1=take.rotations[end,j]
                net=np.rad2deg(2*np.arccos(np.clip(abs(np.dot(q0,q1))/(np.linalg.norm(q0)*np.linalg.norm(q1)),0,1)))
                if end-a<=take.rate*.5 and net<max(15,limit/2):
                    b=end-1; kind='rotation_excursion'; i+=1
            peak=float(np.max(angles[max(0,a-1):min(len(angles),b+1),j]))
            events.append(Event(kind,(n,),a,b,.96 if kind=='rotation_excursion' else .86,
                                f'Joint-local orientation changes by up to {peak:.1f} degrees between samples '
                                f'(threshold {limit:.1f}); quaternion sign changes are ignored.'))
            i+=1
        parent=int(take.parents[j])
        if parent<0: continue
        lengths=np.linalg.norm(take.positions[:,j]-take.positions[:,parent],axis=1)
        base=float(np.nanmedian(lengths))
        deviation=np.abs(lengths-base)
        limit=robust_limit(deviation,max(.005,.05*base))
        for a,b in runs(deviation>limit):
            change=float(np.max(deviation[a:b+1]))
            events.append(Event('bone_length_change',(take.names[parent],n),a,b,.88,
                                f'Parent-to-joint distance departs from its {base*1000:.1f} mm median by '
                                f'up to {change*1000:.1f} mm. Check translation/scale keys and rig intent.'))
    return events
