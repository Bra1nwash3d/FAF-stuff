import json
import random
import threading

distractors = 3


class Questions():
    def __init__(self, bot, chatpointsObj, chateventsObj, jsonpath):
        self.bot = bot
        self.chatpointsObj = chatpointsObj
        self.chateventsObj = chateventsObj
        self.jsonpath = jsonpath
        self.lock = threading.Lock()
        self.questions = {}
        self.current_question = False
        self.current_answers = {}
        try:
            with open(self.jsonpath, 'r+') as file:
                self.questions = json.load(file)
        except:
            print('Questions could not be loaded! From: ' + jsonpath)
            pass

    def __output_to_chat(self, channel, msg):
        self.bot.privmsg(channel, msg)

    def __question_as_str(self, q):
        if q.get('c', False):
            # with distractors
            return """Solve for {points} chatpoints: "{question}" Your choices: {choices}""".format(**{
                'points':  q.get('p'),
                'question':  q.get('q'),
                'choices':  " / ".join(q.get('c')),
            })
        # without distractors
        return """Solve for {points} chatpoints: "{question}""".format(**{
            'points':  q.get('p'),
            'question':  q.get('q')
        })

    def get_tags(self, id, channel):
        tags = {}
        for q in self.questions:
            for t in q.get('tags'):
                tags[t] = tags.get('t', 0) + 1
        self.__output_to_chat(channel, "There are {n} questions in total, by tags: {t}".format(**{
            "n": len(self.questions),
            "t": repr(tags),
        }))

    def question(self, id, channel, tag=None):
        self.lock.acquire()
        if self.current_question:
            self.lock.release()
            self.__output_to_chat(channel, "There is already a question to solve!")
            self.__output_to_chat(channel, self.__question_as_str(self.current_question))
            return False, {}
        questions = self.questions
        if tag:
            questions = [q for q in self.questions if tag in q.get("tags", [])]
            if len(questions) == 0:
                self.lock.release()
                return False, "No question for tag {} available".format(tag)
        i = random.randint(0, len(questions)-1)
        q = questions[i]
        self.current_question = {
            'by': id,
            'req_tag': tag,
            'channel': channel,
            'i': i,
            'q': q.get("q"),
            'a': q.get("a")[random.randint(0, len(q.get("a"))-1)],
            'p': random.randint(q.get('p')[0], q.get('p')[1]),
        }
        if q.get('d'):
            c = random.sample(q.get("d"), distractors) + [self.current_question.get('a')]
            random.shuffle(c)
            self.current_question['c'] = c
        self.lock.release()
        self.__output_to_chat(channel, self.__question_as_str(self.current_question))
        return True, self.current_question

    def answer(self, id, channel, answer):
        self.lock.acquire()
        if not self.current_question:
            self.lock.release()
            return False
        if self.current_answers.get(id):
            self.lock.release()
            self.__output_to_chat(id, "You already attempted an answer!")
            return False
        answer = (" ".join(answer)).lower()
        self.current_answers[id] = answer
        if answer == self.current_question.get('a', '').lower():
            self.current_question['answers'] = self.current_answers
            self.chatpointsObj.updateById(id, delta={'p' : self.current_question.get('p', 0)},
                                          allowNegative=False,
                                          partial=False)
            self.chatpointsObj.updateById(id, delta={'questions' : self.current_question.get('p', 0)},
                                          allowNegative=False,
                                          partial=False)
            self.chateventsObj.addEvent('question', self.current_question)
            self.current_question = {}
            self.current_answers = {}
            self.lock.release()
            self.__output_to_chat(channel, "{} answered correctly!".format(id))
            return True
        self.lock.release()
        return False
