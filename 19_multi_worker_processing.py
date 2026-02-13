# After trying debugpy and dbt and going crazy about their inconsistent results and
# inflexibility to switch between processes, I now found that logging/printing with
# `os.getpid()` is the best way for me to trace down what happens and debug.

import os
from time import perf_counter
from typing import NamedTuple
from multiprocessing import Process, SimpleQueue, cpu_count
from multiprocessing import queues
import numpy as np
import math 


def is_prime(n: int) -> bool:
    if n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False

    root = math.isqrt(n)
    for i in range(3, root + 1, 2):
        if n % i == 0:
            return False
    return True

NUMBERS = np.array([
    2,
    3333333333333333,
    4444444444444444,
    5555555555555555,
    6666666666666666,
    142702110479723,
    7777777777777777,
    299593572317531,
    9999999999999999,
    3333333333333301,
    3333335652092209,
    4444444488888889,
    4444444444444423,
    5555553133149889,
    5555555555555503,
    6666666666666719,
    6666667141414921,
    7777777536340681,
    7777777777777753,
    9999999999999917,
], dtype=np.int64)

class PrimeResult(NamedTuple):
    # need to put n into this class, because results don't come back in the same order
    n: int
    prime: bool
    elapsed: float

JobQueue = queues.SimpleQueue[int] # queue to send numbers to the running processes from the main process
ResultQueue = queues.SimpleQueue[PrimeResult] # queue to collect the results on the main process

def check(n):
    t0 = perf_counter()
    res = is_prime(n)
    return PrimeResult(n, res, perf_counter() - t0)

def worker(jobs, results):
    """Worker gets a queue with the numbers to be checked, and another to put results."""
    while n := jobs.get(): # keep looping while the value fetched from the queue is truthy
        print(f"{os.getpid()} Consume from 'job': {n}")
        print(f"{os.getpid()} Put into 'results': {check(n)}")
        results.put(check(n)) # check if n is_prime and enqueue PrimeResult
    print(f"{os.getpid()} Put into 'results': PrimeResult(0, False, 0.0)")    
    results.put(PrimeResult(0, False, 0.0)) # send back a PrimeResult(0, False, 0.0) to let the main loop know that this worker is done

def start_jobs(procs: int, jobs: JobQueue, results: ResultQueue): # procs is the number of processes that will compute the prime checks in parallel
    for n in NUMBERS:
        print(f"{os.getpid()} Put into 'jobs': {n}")
        jobs.put(n) # enqueue the numbers to be checked in jobs
    for _ in range(procs):
        # fork a child process for each worker. Each child will run the loop inside its 
        # own instance of the worker function, until it fetches a 0 from the jobs queue
        proc = Process(target=worker, args=(jobs, results))
        proc.start() # from here on there is another process running, we'll have 14 in total
        print(f"{os.getpid()} Put into 'jobs': 0")
        jobs.put(0) # 0 here is used as a signal for the worker to finish (often None is used for this)

def report(procs: int, results: ResultQueue):
    checked = 0
    procs_done = 0
    while procs_done < procs:
        print(f"{os.getpid()} Consume from 'results': n, prime, elapsed")
        n, prime, elapsed = results.get() # get results is available; blocks the main process until an item is available; it doesn’t return or break if the queue is empty
        if n == 0: # if `n` is zero, then one process exited; increment the `procs_done` count
            procs_done += 1
        else: # otherwise, increment the checked count (to keep track of the numbers checked) and display the results
            checked += 1
            label = 'P' if prime else ' '
            print(f'{n:16}  {label} {elapsed:9.6f}s')
    return checked

def main():
    procs = cpu_count()
    print(f'Checking {len(NUMBERS)} numbers with {procs} processes:')
    t0 = perf_counter()
    jobs: JobQueue = SimpleQueue()
    results: ResultQueue = SimpleQueue()
    start_jobs(procs, jobs, results) # start `proc` processes to consume `jobs` and post `results`
    checked = report(procs, results) # retrieve the results and display them
    elapsed = perf_counter() - t0
    print(f'{checked} checks in {elapsed:.2f}s')

main()

# Though in this example I think we have missed to join the 14 processes into main in
# the end.