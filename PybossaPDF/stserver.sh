source ../pybossa/env/bin/activate
redis-server ../pybossa/contrib/sentinel.conf --sentinel
python ../pybossa/run.py
