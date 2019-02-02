from modules.markov import Markov


path_in = './../data/misc/processed_aeolus.txt'
path_out = './../data/misc/aeolus.json'

m = Markov(None, path_out)
m.add_file(path_in, "RAW")
m.save()

print('done!')
