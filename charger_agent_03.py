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

    def __init__(self, *args, **kwargs):
        super(ChargerAgent, self).__init__(*args, **kwargs)

        self._entity = Entity()
        self._address = Address(self._entity)

        with open("../03_full_contract.etch", "r") as fb:
            self._source = fb.read()

        self.prepare_contract(22)

    def prepare_contract(self, price):
        # Setting API up
        self._api = LedgerApi('127.0.0.1', 8100)

        self.longitude = 10
        self.latitude = 10

        self.scheduler = {}

        self.price = price
        self.rate = 22
        self.max_count = 10

        # Need funds to deploy contract
        self._api.sync(self._api.tokens.wealth(self._entity, 5000000))

        # Create contract
        self._contract = SmartContract(self._source)

        # Deploy contract
        self._api.sync(self._api.contracts.create(self._entity, self._contract, 2456766))

        self.chargers = [Entity(), ]

        #self._contract.action(self._api, 'test', 2456755, [self._entity], Address(self.chargers[0]), Address(self.chargers[0]))

        self._contract.action(self._api, 'addCharger', 2456766, [self._entity],
                              Address(self.chargers[0]), self.longitude, self.latitude, self.price, self.rate, self.max_count)
        
        scooter = Entity()
        scooter_start_time = 150000
        scooter_end_time = 151000
        tx_digest = self._contract.action(self._api, 'book', 2456766, [self._entity], Address(self.chargers[0]),
                              Address(scooter), scooter_start_time, scooter_end_time)
        time.sleep(3)
       
        tx_status = self._api.tx.status(tx_digest)
        if tx_status == "Executed":
            self.scheduler[str(Address(scooter))] = [scooter_start_time, scooter_end_time]

        query = self._contract.query(api=self._api, name='getSlotInfo', charger=Address(self.chargers[0]))
        print(query)


    def on_cfp(self, msg_id: int, dialogue_id: int, origin: str, target: int, query: CFP_TYPES):
        """Send a simple Propose to the sender of the CFP."""
        print("[{0}]: Received CFP from {1}".format(self.public_key, origin))

        price = self.price

        # prepare the proposal with a given price.
        proposal = Description({"price_per_energy_percent": price, "digest": str(self._contract.digest),
                                "longitude": self.longitude, "latitude": self.latitude, 
                                "scheduler": json.dumps(self.scheduler), "rate": self.rate, "max_count": self.max_count
        })
        print("[{}]: Sending propose at price: {}".format(self.public_key, price))
        self.send_propose(msg_id + 1, dialogue_id, origin, target + 1, [proposal])

    def on_accept(self, msg_id: int, dialogue_id: int, origin: str, target: int):
        """Once we received an Accept, send the requested data."""
        print("[{0}]: Received accept from {1}."
              .format(self.public_key, origin))

        # Preparing contract
        # PLACE HOLDER TO PREPARE AND SIGN TRANSACTION
        print(self._contract)
        contract = {"digest": str(self._contract.digest), "owner": str(self._contract.owner),
                    "chargers": [str(Address(s)) for s in self.chargers]}

        # Sending contract
        encoded_data = json.dumps(contract).encode("utf-8")
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
