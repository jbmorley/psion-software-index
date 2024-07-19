#!/bin/bash

# Ensure ISOs are mounted.
open /Users/jbmorley/Software/Disks/3-Lib/3LIBJUNE05.dmg
open /Users/jbmorley/Software/Psion/Libraries/psion_worldonline.iso

# Run the full generation.
python3 dumpapps.py library.yaml
