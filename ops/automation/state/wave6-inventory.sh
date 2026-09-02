#!/bin/bash
# Inventory wave-6 candidate leaves vs existing development dirs (lean output)
cd "$(git rev-parse --show-toplevel)"
for d in airfoil-geometry oblique-shock dynamic-stability descent-performance \
         pursuit-guidance inertial-navigation load-spectrum-counting \
         material-selection life-cycle-cost fuselage-sizing; do
  if [ -d "development/$d" ]; then
    echo "EXISTS  $d :: $(ls development/$d | tr '\n' ' ')"
  else
    echo "MISSING $d"
  fi
done
echo
echo "ALL development leaf dirs:"
ls -1 development/ | sort
echo "count: $(ls -1 development/ | wc -l)"
