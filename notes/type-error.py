import sys
import optparse

WORKERS = []


def spawn_worker():
    print('Spawning worker...')
    WORKERS.append(1234)     # dummy PID


def spawn_workers(n):
    while len(WORKERS) < n:
        spawn_worker()


def main():
    parser = optparse.OptionParser()
    parser.add_option('-p', '--processes', dest='processes', default=1)
    options, args = parser.parse_args()
    spawn_workers(options.processes)


if __name__ == '__main__':
    sys.exit(main())
