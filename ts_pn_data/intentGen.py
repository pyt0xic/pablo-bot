from secrets import choice, randbelow


class intentGen:
    def __init__(self, substances):
        self.names = []
        for x in substances:
            self.names.append(x)
            if not substances[x] == []:
                for y in substances[x]:
                    self.names.append(y)

    def parse(self, intent_name, intent_list):
        intent_str = f"- intent: {intent_name}\n  examples: |\n"
        for x in intent_list:
            intent_str = "".join([intent_str, f"    - {x}\n"])
        return intent_str

    def what_is(self):
        what_is_intents = []
        for name in self.names:
            unlikely_chance = randbelow(10)
            templates = [
                f"what is [{name}](substance)?",
                f"what is [{name}](substance)",
                f"whats [{name}](substance)",
                f"what's [{name}](substance)?",
                f"what [{name}](substance)",
            ]
            what_is_intents.append(choice(templates))
            if unlikely_chance > 6:
                unlikely_templates = [
                    f"[{name}](substance)?",
                    f"[{name}](substance) is what?",
                    f"[{name}](substance) is?",
                ]
                what_is_intents.append(choice(unlikely_templates))
        return self.parse("what_is_substance", intent_list=what_is_intents)
