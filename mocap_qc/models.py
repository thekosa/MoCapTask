from dataclasses import dataclass, field
import numpy as np


@dataclass
class MarkerTake:
    names: tuple[str, ...]
    positions: np.ndarray  # frame, marker, xyz; metres in the C3D coordinate system
    valid: np.ndarray
    rate: float
    metadata: dict = field(default_factory=dict)

    @property
    def frames(self):
        return len(self.positions)


@dataclass
class SkeletonTake:
    names: tuple[str, ...]  # full joint tokens, preserving their unique identity
    parents: np.ndarray
    times: np.ndarray  # seconds since the first sampled pose
    positions: np.ndarray  # fully transformed world-space joint origins, metres
    local_positions: np.ndarray  # joint-local translations, metres
    rotations: np.ndarray  # joint-local unit quaternions, xyzw
    scales: np.ndarray
    metadata: dict = field(default_factory=dict)

    @property
    def rate(self):
        return 1.0 / float(np.median(np.diff(self.times)))


@dataclass(frozen=True)
class Event:
    type: str
    targets: tuple[str, ...]
    start: int
    end: int
    confidence: float
    note: str

    def as_dict(self):
        return dict(
            type=self.type,
            targets=list(self.targets),
            start=int(self.start),
            end=int(self.end),
            confidence=round(float(self.confidence), 3),
            note=self.note,
        )


@dataclass
class Alignment:
    offset: int
    method: str
    score: float
    details: dict = field(default_factory=dict)
