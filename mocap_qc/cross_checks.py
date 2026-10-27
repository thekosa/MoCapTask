"""Add time-aligned context without assuming that markers coincide with joint origins."""
from dataclasses import replace
import numpy as np
from .alignment import marker_indices, pelvis_center
from .numerics import angular_steps

MARKER_JOINT = {}
for joint, markers in {
    'Head': ('ARIEL','LFHD','RFHD','LBHD','RBHD'),
    'LeftForeArm': ('LELB','LBEL'),
    'RightForeArm': ('RELB','RBEL'),
    'LeftHand': ('LIWR','LOWR','LIHAND','LOHAND'),
    'RightHand': ('RIWR','ROWR','RIHAND','ROHAND'),
    'LeftLeg': ('LKNE','LKNU'),
    'RightLeg': ('RKNE','RKNU'),
    'LeftFoot': ('LANK','LHEL'),
    'RightFoot': ('RANK','RHEL'),
}.items():
    MARKER_JOINT.update({m: joint for m in markers})


def bridge_amplitude(points, start, end):
    if start < 1 or end + 1 >= len(points):
        return None
    segment = points[start-1:end+2]
    if not np.isfinite(segment).all():
        return None
    bridge = np.linspace(segment[0],segment[-1],len(segment))
    return float(np.max(np.linalg.norm(segment[1:-1]-bridge[1:-1],axis=1)))


def add_context(events, markers, skeleton, alignment):
    short = [name.rsplit('/',1)[-1] for name in skeleton.names]
    output = []
    for event in events:
        extra = ''
        confidence = event.confidence
        if event.type == 'skeleton_translation_spike':
            try:
                center, _ = pelvis_center(markers)
                amp = bridge_amplitude(center,event.start,event.end)
                if amp is not None:
                    extra = f' Aligned pelvis-marker centroid bridge deviation: {amp*1000:.1f} mm.'
                    if amp < .005:
                        extra += ' This supports a skeleton-only excursion.'
                        confidence = max(confidence,.96)
            except ValueError:
                pass
        elif event.type == 'spike':
            joint = MARKER_JOINT.get(event.targets[0].rsplit(':',1)[-1].upper())
            if joint and short.count(joint)==1:
                j=short.index(joint)
                frames=np.arange(event.start-1,event.end+2)
                ts=(frames-alignment.offset)/markers.rate
                if ts[0]>=skeleton.times[0] and ts[-1]<=skeleton.times[-1]:
                    track=np.column_stack([np.interp(ts,skeleton.times,skeleton.positions[:,j,k]) for k in range(3)])
                    amp=bridge_amplitude(track,1,len(track)-2)
                    if amp is not None:
                        extra=f' Aligned {joint} joint-origin bridge deviation: {amp*1000:.1f} mm.'
                        if amp<.005:
                            confidence=min(.97,confidence+.02)
        elif event.type == 'rotation_excursion':
            side = 'R' if event.targets[0].endswith('/RightForeArm') else ('L' if event.targets[0].endswith('/LeftForeArm') else None)
            if side:
                ids=marker_indices(markers.names,(side+'IWR',side+'OWR'))
                a=max(0,event.start-1); b=min(markers.frames-1,event.end+1)
                if len(ids)==2 and markers.valid[a:b+1,ids].all():
                    axis=markers.positions[a:b+1,ids[1]]-markers.positions[a:b+1,ids[0]]
                    norms=np.linalg.norm(axis,axis=1)
                    if np.all(norms>.001):
                        axis=axis/norms[:,None]
                        angles=np.rad2deg(np.arccos(np.clip(np.sum(axis[1:]*axis[:-1],axis=1),-1,1)))
                        maximum=float(np.max(angles))
                        extra=f' Across the aligned interval, the two wrist markers change their connecting-axis direction by at most {maximum:.1f} degrees per C3D frame.'
                        if maximum<5: confidence=max(confidence,.97)
        output.append(replace(event, note=event.note+extra, confidence=confidence))
    return output
