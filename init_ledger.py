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

class InitLedger(OEFAgent):
    """Class that implements the behaviour of the charger agent."""

    def __init__(self, *args, **kwargs):
        super(InitLedger, self).__init__(*args, **kwargs)

        self._entity = Entity()
        self._address = Address(self._entity)

        with open("../02_full_contract.etch", "r") as fb:
            self._source = fb.read()

        self.prepare_contract()

    def prepare_contract(self):
        # Setting API up
        self._api = LedgerApi('127.0.0.1', 8100)

        # Need funds to deploy contract
        self._api.sync(self._api.tokens.wealth(self._entity, 5000000))

        # Create contract
        self._contract = SmartContract(self._source)

        # Deploy contract
        self._api.sync(self._api.contracts.create(self._entity, self._contract, 2456766))

        ff = open('contract.txt', 'w')
        ff.write(str(self._contract._digest) + "\n")
        ff.write(str(Address(self._entity)))
        ff.close()

if __name__ == "__main__":

    agent = InitLedger("contract", oef_addr="127.0.0.1", oef_port=10000)
    #agent.connect()

    #agent.register_service(77, agent.charger_description)

    '''
    print("[{}]: Waiting for clients...".format(agent.public_key))
    try:
        agent.run()
    finally:
        try:
            agent.stop()
            agent.disconnect()
        except:
            pass
    '''
