#!/usr/bin/env python3
"""Print all pose parameter indices for the tha3 model."""

import sys
from pathlib import Path

# Add tha3_repo to path
tha3_path = Path(__file__).parent / "tha3_repo"
sys.path.insert(0, str(tha3_path))

from tha3.poser.modes.pose_parameters import get_pose_parameters

pose_params = get_pose_parameters()

print("=" * 70)
print("THA3 Model Pose Parameters")
print("=" * 70)

index = 0
total_params = 0
for group in pose_params.get_pose_parameter_groups():
    total_params += group.get_arity()

print(f"\nTotal parameters: {total_params}\n")

index = 0
for group in pose_params.get_pose_parameter_groups():
    arity = group.get_arity()
    param_names = group.get_parameter_names()
    
    print(f"{group.group_name} ({group.category.name}):")
    for i, name in enumerate(param_names):
        print(f"  [{index + i:2d}] {name}")
    
    index += arity
    print()

print("=" * 70)
