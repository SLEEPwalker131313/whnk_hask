import pickle
import json
import pprint


from optimize import *
from path import make_path, in_between
from typing import List
from oef.agents import OEFAgent
from oef.proxy import PROPOSE_TYPES
from oef.messages import CFP_TYPES
from oef.schema import Description
from oef.query import Query, Eq, Constraint
from fetchai.ledger.api import LedgerApi
from fetchai.ledger.contract import SmartContract
from fetchai.ledger.crypto import Entity, Address

from charger_schema import PRICE_PER_ENERGY_PERCENT, JOURNEY_MODEL

import time

import sys
import asyncio

class ScooterAgent(OEFAgent):
    """Class that implements the behaviour of the scooter agent."""

    def __init__(self, *args, start=(30.28, 59.91), finish=(30.34, 59.97), n_points=3, charge=0.6, **kwargs):
        super(ScooterAgent, self).__init__(*args, **kwargs)

        self._api = LedgerApi('127.0.0.1', 8100)
        self._entity = Entity()

        self.speed = 0.0005


        self._api.sync(self._api.tokens.wealth(self._entity, 5000000))
        self._address = Address(self._entity)

        with open("../02_full_contract.etch", "r") as fb:
            self._source = fb.read()

        # Create contract
        self._contract = SmartContract(self._source)

        # Deploy contract
        self._api.sync(self._api.contracts.create(self._entity, self._contract, 2456766))


        with open('contract.txt','r') as ff:
            self.digest = ff.readline().split('\n')[0]
            self.owner = ff.readline()

        self._loop = asyncio.get_event_loop()

        self.provider = Entity()
        self.scooter = Entity()

        self.path = make_path(start, finish, n_points, 0.01)
        self.charge = charge

        self._contract.action(self._api, 'addProvider', 2456, [self._entity, self.provider],
                              Address(self.provider), self._address)

        self._contract.action(self._api, 'addScooter', 2456, [self.provider], Address(self.scooter),
                              Address(self.provider), int(start[1]*1000), int(start[0]*1000), 100, 1, 15)


    def on_search_result(self, search_id: int, agents: List[str]):
        if len(agents) == 0:
            print("[{}]: No agent found. Stopping...".format(self.public_key))
            self.stop()
            return

        print("[{0}]: Agent found: {1}".format(self.public_key, agents))
        for agent in agents:
            print("[{0}]: Sending to agent {1}".format(self.public_key, agent))
            # we send a 'None' query, meaning "give me all the resources you can propose."
            query = None
            self.send_cfp(1, 0, agent, 0, query)

        self.saved_proposals = []

        self._loop.call_later(3, self.decide_on_proposals)

    def on_propose(self, msg_id: int, dialogue_id: int, origin: str, target: int, proposals: PROPOSE_TYPES):
        print("[{0}]: Received propose from agent {1}".format(self.public_key, origin))
        for i, p in enumerate(proposals):
            print("[{0}]: Proposal {1}: {2}".format(self.public_key, i, p.values))
            self.saved_proposals.append(((msg_id, dialogue_id, origin, msg_id + 1), p))

        # self.send_accept(msg_id, dialogue_id, origin, msg_id + 1)


    def decide_on_proposals(self):
        print('Got proposals:', self.saved_proposals)

        proposals = [{
            'address': p[1].values['charger_address'],
            'longitude': p[1].values['longitude'],
            'latitude':  p[1].values['latitude'],
            'max_count': p[1].values['max_count'],
            'rate': p[1].values['rate'],
            'scheduler': json.loads(p[1].values['scheduler']),
            'args': p[0]
        } for p in self.saved_proposals]

        best_proposal, best_slot, new_path = find_best(self.path, proposals, self.charge, 0.00001, self.speed)

        dict = {
                'address': str(Address(self.scooter)), 'startTime': best_slot[0],
                'endTime': best_slot[1]
               }
        encoded_data = json.dumps(dict).encode("utf-8")
        print("[{0}]: Sending contract to {1}".format(self.public_key, best_proposal['args'][2]))

        self.send_message(0, best_proposal['args'][1], best_proposal['args'][2], encoded_data)

        time.sleep(5)
        self.send_accept(best_proposal['args'][0], best_proposal['args'][1], best_proposal['args'][2],
                        best_proposal['args'][3])

        self.path = new_path
        self._loop.create_task(self.go())

    async def go(self):

        start_time = time.time()

        while True:
            await asyncio.sleep(1)
            delte_time = time.time() - start_time

            walked_distance = self.speed*delte_time

            current_pos = 0

            new_position = None

            for i in range(len(self.path) - 1):

                d = dist(self.path[i], self.path[i+1])

                if current_pos + d >= walked_distance:
                    alpha = (walked_distance - current_pos) / d
                    new_position = in_between(self.path[i], self.path[i+1], alpha)
                    print(self._address, 'Path', self.path)
                    print(self._address, 'Next point', self.path[i+1])
                    break
                else:
                    current_pos += d

            if new_position is None:
                raise Exception("That's all, folks!")

            self._contract.action(self._api, 'scooterUpdate', 2456, [self.provider],
                                       Address(self.scooter), int(new_position[1]*1000), int(new_position[0]*1000), int(self.charge*100))

        #tx_digest = self._contract.action(self._api, 'book', 2456766, [self._entity], best_proposal['address'], Address(self.scooters[0]), best_slot[0], best_slot[1])
        #time.sleep(3)
        #print("Failed tx:", tx_digest)
        #tx_status = self._api.tx.status(tx_digest)
        #if tx_status == "Executed":
            #self.scheduler[self.scooterToBook] = [self.scooter_start_time, self.scooter_end_time]

        #    encoded_data = json.dumps(tx_digest).encode("utf-8")
        #    print("[{0}]: Sending contract to {1}".format(self.public_key, origin))
        #    self.send_message(0, dialogue_id, origin, encoded_data)

if __name__ == "__main__":

    name = sys.argv[1]

    print('Name:', name)

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
