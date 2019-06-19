import pickle
import json
import pprint
import time

from charger_schema import JOURNEY_MODEL
from oef.agents import OEFAgent
from oef.messages import CFP_TYPES
from oef.schema import Description
from fetchai.ledger.api import LedgerApi
from fetchai.ledger.contract import SmartContract
from fetchai.ledger.crypto import Entity, Address

import sys

class ChargerAgent(OEFAgent):
    """Class that implements the behaviour of the charger agent."""

    charger_description = Description(
        {
            "price_per_energy_percent": True,
        },
        JOURNEY_MODEL
    )

    def __init__(self, *args, latitude=59.94, longitude=30.31, **kwargs):
        super(ChargerAgent, self).__init__(*args, **kwargs)

        self.longitude = longitude
        self.latitude = latitude

        self._entity = Entity()
        self._address = Address(self._entity)

        #with open("../02_full_contract.etch", "r") as fb:
        #    self._source = fb.read()

        self.prepare_contract(22)

    def prepare_contract(self, price):
        # Setting API up
        self._api = LedgerApi('127.0.0.1', 8100)

        self.scheduler = {}

        self.price = price
        self.rate = 20
        self.max_count = 10

        # Need funds to deploy contract
        self._api.sync(self._api.tokens.wealth(self._entity, 5000000))

        # Create contract
        #self._contract = SmartContract(self._source)

        # Deploy contract
        #self._api.sync(self._api.contracts.create(self._entity, self._contract, 2456766))

        with open('contract.txt','r') as ff:
            self.digest = ff.readline().split('\n')[0]
            self.owner = ff.readline()

        self.chargers = [Entity(), ]

        self._api.contracts.action(self.digest, self.owner, 'addCharger', 2456766, [self._entity],
                              Address(self.chargers[0]), self.longitude, self.latitude, self.price, self.rate, self.max_count)

        #query = self._contract.query(api=self._api, name='getSlotInfo', charger=Address(self.chargers[0]))
        #print(query)


    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        """Send a simple Propose to the sender of the CFP."""
        print("[{0}]: Received CFP from {1}".format(self.public_key, origin))

        price = self.price
        
        timeArr = []
        for key in self.scheduler.keys():
            timeArr.append(self.scheduler[key])
        
        # prepare the proposal with a given price.
        proposal = Description({"price_per_energy_percent": price, "digest": self.digest,
                                "longitude": self.longitude, "latitude": self.latitude, 
                                "scheduler": json.dumps(timeArr), "rate": self.rate, "max_count": self.max_count,
                                "charger_address": str(Address(self.chargers[0]))
        })
        print("[{}]: Sending propose at price: {}".format(self.public_key, price))
        self.send_propose(msg_id + 1, dialogue_id, origin, target + 1, [proposal])

    def on_message(self, msg_id: int, dialogue_id: int, origin: str, content: bytes):
        """Extract and print data from incoming (simple) messages."""

        # PLACE HOLDER TO SIGN AND SUBMIT TRANSACTION
        json_bla = json.loads(content.decode("utf-8"))
        print("[{0}]: Received contract from {1}".format(self.public_key, origin))
        print("READY TO SUBMIT: ", json_bla['address'])

        self.scooterToBook = Address(json_bla['address'])
        self.scooter_start_time = json_bla['startTime']
        self.scooter_end_time = json_bla['endTime']

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """Once we received an Accept, send the requested data."""
        print("[{0}]: Received accept from {1}."
              .format(self.public_key, origin))

        # Preparing contract
        # PLACE HOLDER TO PREPARE AND SIGN TRANSACTION

        print(self.scooterToBook)
        print(Address(self.scooterToBook))
        print("trying to BOOK /////")

        tx_digest = self._api.contracts.action(self.digest, self.owner, 'book', 2456766, [self.chargers[0]], Address(self.chargers[0]),
                                          self.scooterToBook, self.scooter_start_time, self.scooter_end_time)
        time.sleep(3)
        print("Failed tx:", tx_digest)
        tx_status = self._api.tx.status(tx_digest)
        if tx_status == "Executed":
            self.scheduler[self.scooterToBook] = [self.scooter_start_time, self.scooter_end_time]

            encoded_data = json.dumps(tx_digest).encode("utf-8")
            print("[{0}]: Sending contract to {1}".format(self.public_key, origin))
            self.send_message(0, dialogue_id, origin, encoded_data)


if __name__ == "__main__":

    name = sys.argv[1]

    print('name', name)

    agent = ChargerAgent(name, oef_addr="127.0.0.1", oef_port=10000)
    agent.connect()
    agent.register_service(77, agent.charger_description)

    print("[{}]: Waiting for clients...".format(agent.public_key))
    try:
        agent.run()
    finally:
        try:
            agent.stop()
            agent.disconnect()
        except:
            pass
