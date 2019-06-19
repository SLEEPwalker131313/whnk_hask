import time
from math import sqrt

def argmin(l, f):
	f_l = [f(e) for e in l]

	m = min(f_l)
	for i, e in enumerate(f_l):
		if e == m: return l[i]

def dist(A, B):
	return sqrt((A[0] - B[0]) ** 2 + (A[1] - B[1]) ** 2)



def length(trajectory):
	return sum([dist(trajectory[i], trajectory[i+1]) for i in range(len(trajectory) - 1)])


def find_slot(schedule, arrival, charging_time, max_count):
        startTime = arrival
        endTime = arrival + charging_time
        
        counter = 0
        for addressTime in schedule:
            if (int(addressTime[0]) <= startTime and startTime <= int(addressTime[1]) or
                int(addressTime[0]) <= endTime and endTime <= int(addressTime[1]) or
                int(addressTime[0]) >= startTime and int(addressTime[0]) <= endTime or
                int(addressTime[1]) >= startTime and int(addressTime[1]) <= endTime):
                 counter += 1
        if counter >= max_count:
            return None
        else:
            return [startTime, endTime]

        '''
	appointment = schedule[-1][1]

	if arrival > appointment:
		return (arrival, appointment + charging_time)
	
	for idx in range(len(schedule) - 1):

		release = schedule[idx][1]
		lock = schedule[idx+1][0]

		if lock - release < charging_time or lock - charging_time < arrival:
			continue

		appointment = max(arrival, release)
		break

	return (appointment, appointment + charging_time)
        '''


def find_best(trajectory, proposals, charge, mpg, speed):

	best_time = None
	best_address = None
	best_slot = None
	best_proposal = None

	for psl in proposals:
		max_count = psl['max_count']
		new_point = (psl['longitude'], psl['latitude'])
		charging_speed = psl['rate']
		dists = [dist(e, new_point) for e in trajectory]
		m = min(dists)

		min_idx = next(filter(lambda i: dists[i] == m, range(len(dists))), -1)

		distance = length([*trajectory[:min_idx], new_point])

		charge_left = charge - (distance * mpg)

		if charge_left < 0:
			continue

		arrival = time.time() + distance / speed

		charging_time =  (1 - charge_left) / charging_speed

		slot = find_slot(psl['scheduler'], arrival, charging_time, max_count)

		finish_time = slot[1] + length([new_point, *trajectory[min_idx+1:]]) / speed
		print(psl['address'], finish_time)

		if best_time is None or best_time > finish_time:
			best_time = finish_time
			best_trajectory = [*trajectory[:min_idx], new_point, *trajectory[min_idx+1:]]
			best_proposal = psl
			best_slot = slot

	if best_time is None:
		raise Exception("You are doomed, better luck next time")

	return best_proposal, best_slot, best_trajectory


cur_time = time.time()

proposals = [
	{
		"address": 'blah blah blah',
		"longitude": 5,
                "latitude": 5,
                "max_count": 10,
		"scheduler": [(cur_time + 6, cur_time + 9), (cur_time + 15, cur_time+19)]
	}, {
		"address": 'blah blah blah 2: Electric boongaloo',
		"longitude": 5,
                "latitude": 5,
                "max_count": 10,
		"scheduler": [(cur_time + 3, cur_time + 4), (cur_time + 21, cur_time+3)]
	},
]
trajectory = [(1, 1), (3,4), (6, 4), (7,6), (8, 8)]

# print(find_best(trajectory, proposals, 0.6, 0.05, 1))



