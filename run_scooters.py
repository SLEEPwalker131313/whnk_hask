from scooter_agent import *
from multiprocessing.dummy import Pool
import random
import string
from argparse import ArgumentParser
import asyncio

counter = 0
def get_name():
    global counter
    counter = counter + 1
    return "scooter" + str(counter)

def random_string(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def run_scooter_agent(name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    agent = ScooterAgent(name, oef_addr="127.0.0.1", oef_port=10000)
    agent.connect()

    time.sleep(2)


    query = Query([Constraint(PRICE_PER_ENERGY_PERCENT.name, Eq(True))],
                  JOURNEY_MODEL)

    agent.search_services(0, query)

    time.sleep(1)

    print("[{}]: Waiting for clients...".format(agent.public_key))
    try:
        agent.run()
    finally:
        try:
            agent.stop()
            agent.disconnect()
        except:
            pass

def main():
    parser = ArgumentParser()
    parser.add_argument('--num', type=int, default=200, help='Number of agents to run')
    opts = parser.parse_args()

    num_scooters = opts.num
    names = []

    for i in range(0, num_scooters):
        name = get_name()
        names.append(name)
    
    pool = Pool(num_scooters)
    pool.map(run_scooter_agent, names)
    pool.close()
    pool.join()

    #for name in names:
    #    run_scooter_agent(name)

if __name__ == "__main__":
    main()

