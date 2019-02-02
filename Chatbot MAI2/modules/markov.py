import json
import codecs
import random
import traceback
import io
from modules.utils import get_logger

logger = get_logger('markov')

# dict keys
WF = 'wf'   # words forward
UF = 'uf'   # uses forward
WB = 'wb'   # words backward
UB = 'ub'   # uses backward
WD = 'wd'   # word disabled
CS = 'cs'   # counter start sentence with word
CE = 'ce'   # counter end sentence with word


class Markov:
    """
    create word chains, based on how likely words appear in sequence in the given sample data
    create a new wordfile based on /quick_tests/create_markov_json.py, just feed some raw text
    """

    def __init__(self, plugin, wordfilepath, min_chain_length=4, max_chain_length=20, chain_length_chance=0.92):
        self.plugin = plugin
        self.wordfilepath = wordfilepath
        self.markovwords = {}
        self.min_chain_length = min_chain_length
        self.max_chain_length = max_chain_length
        self.chain_length_chance = chain_length_chance
        try:
            with codecs.open(self.wordfilepath, mode='r+', encoding='utf8') as file:
                self.markovwords = json.load(file)
        except Exception:
            print(traceback.format_exc())
            pass

    def get_info(self):
        return "[path: " + self.wordfilepath + ", count: " + str(len(self.markovwords)) + "]"

    def save(self, path=None):
        path = path if path is not None else self.wordfilepath
        with io.open(path, 'w+', encoding='utf8') as file:
            file.write(json.dumps(self.markovwords, indent=2, ensure_ascii=False))
            file.close()

    def add_file(self, filename, filetype="LOG"):
        """
        Add content of a file to the markov words
        """
        file = codecs.open(filename, encoding='utf-8')
        if filetype == "LOG":
            for line in file:
                linesplit = line.replace("\n", "").split("> ", maxsplit=1)
                if len(linesplit) < 2:
                    continue
                self.add_line(linesplit[1])
        elif filetype == "RAW":
            for line in file:
                line.replace("\n", "")
                self.add_line(line)
        file.close()

    def add_line(self, line):
        if line.startswith("!"):
            return
        words = line.replace('\n', '').replace('\r', '').replace('\t', '').split()
        if len(words) < 2:
            return
        # forwards chain probs
        for i in range(0, len(words) - 1):
            wg = self.markovwords.get(words[i], Markov._get_word_template())
            wg[WF][words[i + 1]] = wg[WF].get(words[i + 1], 0) + 1
            wg[UF] = wg[UF] + 1
            self.markovwords[words[i]] = wg
        # backwards chain probs
        for i in range(1, len(words)):
            wg = self.markovwords.get(words[i], Markov._get_word_template())
            wg[WB][words[i - 1]] = wg[WB].get(words[i - 1], 0) + 1
            wg[UB] = wg[UB] + 1
            self.markovwords[words[i]] = wg
        # start / uses / end counter
        wg = self.markovwords.get(words[-1], Markov._get_word_template())
        wg[CE] = wg[CE] + 1
        wg[UF] = wg[UF] + 1
        self.markovwords[words[-1]] = wg
        wg = self.markovwords.get(words[0], Markov._get_word_template())
        wg[CS] = wg[CS] + 1
        wg[UB] = wg[UB] + 1
        self.markovwords[words[0]] = wg

    @staticmethod
    def _get_word_template():
        return {CE: 0, UF: 0, WF: {},
                CS: 0, UB: 0, WB: {}}

    def pick_random_start_word(self):
        keys = self.markovwords.keys()
        word = False
        for i in range(1000):
            word = random.sample(keys, 1)[0]
            wordgroup = self.markovwords[word]
            if random.random() < (wordgroup.get(CS, 0)/wordgroup.get(UF, 1)):
                return word
        return word

    def sentence(self, word, channel, target_length=None, include_word=False, forward=True):
        if not word:
            word = self.pick_random_start_word()
        target_length = target_length if target_length is not None else self.__random_chain_length()
        subgroup = WF if forward else WB
        sentence = []
        if include_word:
            sentence.append(word)
        for i in range(0, target_length):
            word_group = self.markovwords.get(word, False)
            if self.__decide_to_start_end(Markov.__start_end_sentence_prob(word_group, start=False), i, target_length):
                break
            if word_group and len(word_group[subgroup]) > 0:
                word, stop = False, True
                for _ in range(10):
                    word, _ = Markov.pick_weighted_random(word_group[subgroup])
                    if self.__is_suitable_chain_wordb(word, channel):
                        stop = False
                        break
                if stop:
                    break
                sentence.append(word)
            else:
                break
        if not forward:
            sentence = sentence[::-1]
        return ' '.join(sentence)

    def chainprob(self, word1, word2=False):
        if not word2:
            word_group = self.markovwords.get(word1, Markov._get_word_template())
            return 'Probabilities: start sentence {start}, end sentence {end}'.format(**{
                "start": format(Markov.__start_end_sentence_prob(word_group, start=True), '.4f'),
                "end": format(Markov.__start_end_sentence_prob(word_group, start=False), '.4f'),
            })
        word_group_f = self.markovwords.get(word1, Markov._get_word_template())
        totalf = word_group_f[UF]
        countf = word_group_f[WF].get(word2, 0)
        word_group_b = self.markovwords.get(word2, Markov._get_word_template())
        totalb = word_group_b[UB]
        countb = word_group_b[WB].get(word1, 0)
        if totalf <= 0:
            return 'Word ' + word1 + " has never been used."
        if totalb <= 0:
            return 'Word ' + word1 + " has never been used."
        return 'Probabilities: forward {countf}/{totalf}, backward {countb}/{totalb}'.format(**{
            "countf": countf,
            "totalf": totalf,
            "pf": countf/totalf,
            "countb": countb,
            "totalb": totalb,
            "pb": countb/totalb,
        })

    def __decide_to_start_end(self, p, i, maxi):
        if i < self.min_chain_length:
            return False
        return random.random() < (p * (1 + i/maxi))

    @staticmethod
    def __start_end_sentence_prob(word_group, start=True):
        cx, ux = (CS, UB) if start else (CE, UF)
        if word_group:
            return max([0, (word_group.get(cx, 0) / max([word_group.get(ux, 0), 1])) - 0.02])
        return 1

    @staticmethod
    def pick_weighted_random(dct: dict):
        total = sum(dct.values())
        v = random.random() * total
        for key in dct.keys():
            v -= dct[key]
            if v <= 0:
                return key, total
        return list(dct.keys())[-1], total

    def __is_suitable_chain_wordb(self, word, channel):
        if self.plugin.is_in_channel(word, channel):
            return False
        if "http://" in word or "https://" in word:
            return False
        if self.markovwords.get(word, {}).get(WD, False):
            return False
        return True

    def __random_chain_length(self):
        """ rolls random length, via geometric distribution """
        for i in range(self.min_chain_length, self.max_chain_length):
            if random.random() > self.chain_length_chance:
                return i
        return self.max_chain_length

    def get_word(self, word):
        return self.markovwords.get(word)

    def del_word(self, word):
        # does not prevent the word from appearing at start/end of a sentence, only to chain further
        if self.markovwords.get(word):
            del self.markovwords[word]
            return True
        return False

    def disable_word(self, word):
        word_group = self.markovwords.get(word, False)
        word_group[WD] = True
