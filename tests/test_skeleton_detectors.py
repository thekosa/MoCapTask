import numpy as np
from conftest import make_skeleton, make_markers
from mocap_qc.skeleton_detectors import detect_skeleton
from mocap_qc.numerics import map_skeleton_event
from mocap_qc.models import Event


def test_quaternion_sign_flip_is_not_physical_rotation():
    s=make_skeleton()
    s.rotations[100:170,1]*=-1
    assert detect_skeleton(s)==[]


def test_actual_180_degree_excursion_is_bounded():
    s=make_skeleton()
    s.rotations[40:56,1]=[1,0,0,0]
    events=detect_skeleton(s)
    assert [(e.type,e.start,e.end) for e in events]==[('rotation_excursion',40,55)]


def test_root_spike_is_reported_once_not_on_all_descendants():
    s=make_skeleton()
    s.positions[200,:,0]+=.06
    events=detect_skeleton(s)
    assert [(e.type,e.targets,e.start,e.end) for e in events]==[('skeleton_translation_spike',('Hips',),200,200)]


def test_bone_length_change():
    s=make_skeleton()
    s.positions[100:111,2,0]+=.03
    events=detect_skeleton(s)
    assert [(e.type,e.start,e.end) for e in events]==[('bone_length_change',100,110)]


def test_mapping_uses_first_pose_time_offset_and_rate():
    m=make_markers(); s=make_skeleton(rate=60)
    e=Event('rotation_jump',('Hips',),10,12,.9,'test')
    result=map_skeleton_event(e,s,m,18)
    assert (result.start,result.end)==(38,42)


def test_mapping_clips_and_discards_outside_c3d():
    m=make_markers(); s=make_skeleton()
    e=Event('rotation_jump',('Hips',),0,10,.9,'test')
    result=map_skeleton_event(e,s,m,-5)
    assert (result.start,result.end)==(0,5)
    assert 'clipped' in result.note
    assert map_skeleton_event(e,s,m,400) is None
