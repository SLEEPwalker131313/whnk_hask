from charger_agent_backup import * #ChargerAgent
from multiprocessing.dummy import Pool
import random
import string
from argparse import ArgumentParser
import asyncio
from scooter_agent import * #ScooterAgent
from oef.query import Query
from typing import List
from oef.proxy import PROPOSE_TYPES
from oef.query import Eq, Constraint
from oef.query import Query

from flask import Flask, request, abort, jsonify, send_file
from werkzeug.contrib.cache import SimpleCache
from flask import Response

import time

import os
import shutil

counter_charger = 0
def get_name_charger():
    global counter_charger
    counter_charger = counter_charger + 1
    return "charger" + str(counter_charger)

counter_scooter = 0
def get_name_scooter():
    global counter_scooter
    counter_scooter += 1
    return "scooter" + str(counter_scooter)

def random_string(stringLength=10):
    """Generate a random string of fixed length """
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for i in range(stringLength))

def run_charger_agent(name):
    print(name)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    agent = ChargerAgent(name, oef_addr="127.0.0.1", oef_port=10000)
    agent.connect()
    agent.register_service(77, agent.charger_description)
    
    print(str(Address(agent.chargers[0])))
    with open('db_chargers/' + str(Address(agent.chargers[0])) + '.txt', 'w') as ff:
        ff.write(str(agent._contract._digest) + '\n')
        ff.write(str(agent._contract._owner))


    print("[{}]: Waiting for clients...".format(agent.public_key))
    try:
        agent.run()
    finally:
        try:
            agent.stop()
            agent.disconnect()
        except:
            pass

def run_scooter_agent(name):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    agent = ScooterAgent(name, oef_addr="127.0.0.1", oef_port=10000)
    agent.connect()

    time.sleep(2)
    print(str(Address(agent.scooter)))
    with open('db/' + str(Address(agent.scooter)) + '.txt', 'w') as ff:
        ff.write(str(agent._contract._digest) + '\n')
        ff.write(str(agent._contract._owner))

    #get_scooter_position(Address(agent.scooters[0]))

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

cache = SimpleCache(default_timeout=6000)
cache.set('scooters', [])
cache.set('chargers', ['test'])

app = Flask(__name__)

#@app.route('/get_scooter_position/<address>', methods=["GET",])
def get_scooter_positions():
     api = LedgerApi('127.0.0.1', 8100)
     entity = Entity()

     api.sync(api.tokens.wealth(entity, 5000000))
     
     #address = Address(entity)

     #with open("../02_full_contract.etch", "r") as fb:
     #   source = fb.read()

     # Create contract
     #contract = SmartContract(source)

     # Deploy contract
     #api.sync(api.contracts.create(entity, contract, 2456766))

     ret = []

     for filename in os.listdir('db'):
         address = filename.split('.')[0]
         with open('db/' + filename, 'r') as ff:
             digest = ff.readline().split('\n')[0]
             owner = ff.readline()
     
         queryLan = api.contracts.query(Address(digest), Address(owner), 'getLanScooter', scooter=Address(address))
         queryLng = api.contracts.query(Address(digest), Address(owner), 'getLngScooter', scooter=Address(address))

         if not (queryLan[0] and queryLng[0]):
            continue

         ret.append({
             "type": 2,
             "lat": queryLan[1]['result'] / 1000,
             "lng": queryLng[1]['result'] / 1000,
             "id": owner
         })

     return ret

     #return jsonify(dict)

#@app.route('/get_charger_position/<address>', methods=["GET",])
def get_charger_positions():
     api = LedgerApi('127.0.0.1', 8100)
     entity = Entity()

     api.sync(api.tokens.wealth(entity, 5000000))

     ret = []

     for filename in os.listdir('db_chargers'):
         address = filename.split('.')[0]
         with open('db_chargers/' + filename, 'r') as ff:
             digest = ff.readline().split('\n')[0]
             owner = ff.readline()

         queryLan = api.contracts.query(Address(digest), Address(owner), 'getLanCharger', charger=Address(address))
         queryLng = api.contracts.query(Address(digest), Address(owner), 'getLngCharger', charger=Address(address))

         if not (queryLan[0] and queryLng[0]):
            continue

         ret.append({
             "type": 1,
             "lat": queryLan[1]['result'] / 1000,
             "lng": queryLng[1]['result'] / 1000,
             "id": owner
         })

     return ret

     #return jsonify(dict)


@app.route('/run_scooters/<num>', methods=["GET",])
def run_scooters(num):
    names = []
    num = int(num)

    for i in range(0, num):
        name = get_name_scooter()
        names.append(name)
    
    pool = Pool(num)
    pool.map(run_scooter_agent, names)
    #pool.join()
    #pool.close()
    return "ok", 200

@app.route('/run_chargers/<num>', methods=["GET",])
def run_chargers(num):
    names = []
    num = int(num)

    for i in range(0, num):
        name = get_name_charger()
        names.append(name)
    
    pool = Pool(num)
    pool.map(run_charger_agent, names)
    #pool.close()
    #pool.join()
    return "ok", 200

@app.route('/add/<type>', methods=["POST",])
def add_address(type):
    address = request.json['address']

    if type not in ['scooters', 'chargers']:
        abort(400)

    data = cache.get(type)
    cache.set(type, [*data, address])



'''
[{
    'address',
    'latitude',
    'longitude',
    'type': 'charges'/'scooter'/'ride'
}]
'''

@app.route('/positions')
def add_scooter():
    return jsonify([*get_charger_positions(), *get_scooter_positions()])

@app.route('/img/<name>')
def get_image(name):

    if name not in ['man.png', 'vespa.png', 'battery.png']:
        abort(400)

    return send_file(name)


@app.route('/')
def index():
    return send_file('index.html')




if __name__ == "__main__":
    shutil.rmtree('db')
    shutil.rmtree('db_chargers')

    os.mkdir('db')
    os.mkdir('db_chargers')

    app.run(host='0.0.0.0', port=9089, debug=True)

