from secrets import choice, randbelow
import re


class DataGen:
    def __init__(self, substances):
        self.substance_data = substances
        self.names = []
        for x in substances["substances"]:
            self.names.append(re.sub(r"\(.*\)", "", x["name"]))
            for y in x["aliases"]:
                self.names.append(re.sub(r"\(.*\)", "", y))

    def parse(self, intent_name, intent_list):
        intent_str = f"- intent: {intent_name}\n  examples: |\n"
        for x in intent_list:
            intent_str = "".join([intent_str, f"    - {x}\n"])
        return intent_str

    def query_objects(self):
        intents = []

        # General object queries

        templates = [
            'list all [drugs]{"entity": "object_type", "value": "substances"}',
            'what [drug]{"entity": "object_type", "value": "substances"} is safe?',
            'what [substance]{"entity": "object_type", "value": "substances"} is legal',
            'list all [substances]{"entity": "object_type", "value": "substances"}',
            'can you list the [substances]{"entity": "object_type", "value": "substances"}?',
        ]
        for x in templates:
            intents.append(x)

        return self.parse(intent_name="query_objects", intent_list=intents)

    def query_attributes(self):
        intents = []
        doses = [
            "0.5mg",
            "100mg",
            "600mg",
            "1 gram",
            "one gram",
            "5 grams",
            "55mg",
            "fifty milligrams",
            "ten mgs",
            "1g",
            "4.5g",
            "359mg",
        ]

        for name in self.names:
            unlikely_chance = randbelow(10)
            templates = [
                f"what is [{name}](substances)?",
                f"whats [{name}](substances)",
                f"what's [{name}](substances)?",
                'what is the [toxic dose]{"entity": "attribute", "value": "toxicity"} '
                f"of [{name}](substances)?",
                f"what is the [toxicity](attribute) of [{name}](substances)?",
                'how [toxic]{"entity": "attribute", "value": "toxicity"} '
                f"is [{name}](substances)",
                'how [safe]{"entity": "attribute", "value": "toxicity"} '
                f"is [{name}](substances)",
                'how [dangerous]{"entity": "attribute", "value": "toxicity"} '
                f"is [{name}](substances)?",
                'how [addictive]{"entity": "attribute", "value": "addictionPotential"} '
                f"is [{name}](substances)?",
                f"is [{name}](substances) "
                '[addictive]{"entity": "attribute", "value": "addictionPotential"}?',
                f"is [{name}](substances) "
                '[addicting]{"entity": "attribute", "value": "addictionPotential"}',
                f"is [{name}](substances) "
                '[safe]{"entity": "attribute", "value": "toxicity"}?',
                '[how much]{"entity": "attribute", "value": "roas"} '
                f"[{name}](substances) should i take?",
                '[how much]{"entity": "attribute", "value": "roas"} '
                f"[{name}](substances)?",
                '[how many]{"entity": "attribute", "value": "roas"} '
                f"[{name}](substances) should i have?",
                'what [dose]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances) should i take?",
                'what [dose]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances) do i need",
                'what [dosage]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances) is enough?",
                '[routes of administration]{"entity": "attribute", "value": "roas"} for '
                f"[{name}](substances)?",
                '[roas]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances)",
                f"how much [{name}](substances) should i "
                '[snort]{"entity": "attribute", "value": "roas"}?',
                f"how much [{name}](substances) can i take "
                '[orally]{"entity": "attribute", "value": "roas"}?',
                f"can i take [{name}](substances) via "
                '[oral]{"entity": "attribute", "value": "roas"} administration?',
                '[how long]{"entity": "attribute", "value": "roas"} does '
                f"[{name}](substances) last?",
                '[duration]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances)",
                'what is the [duration]{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances)?",
                '[how long]{"entity": "attribute", "value": "roas"} does '
                f"[{name}](substances) take to peak?",
                '[interactions]{"entity": "attribute", "value": "interactions"} of '
                f"[{name}](substances)",
                f"[{name}](substances) "
                '[interactions]{"entity": "attribute", "value": "interactions"}',
                f"what does [{name}](substances) "
                '[interact]{"entity": "attribute", "value": "interactions"} with?',
                f"what drugs does [{name}](substances) "
                '[interact]{"entity": "attribute", "value": "interactions"} with?',
                'what substance [mixes]{"entity": "attribute", "value": "interactions"} with '
                f"[{name}](substances)",
                'what substances [mix]{"entity": "attribute", "value": "interactions"} with '
                f"[{name}](substances)",
                'what [interacts]{"entity": "attribute", "value": "interactions"} with '
                f"[{name}](substances)?",
                'what [synergizes]{"entity": "attribute", "value": "interactions"} with '
                f"[{name}](substances)",
                'what [mixes]{"entity": "attribute", "value": "interactions"} well with '
                f"[{name}](substances)?",
                'what kind of [chemical]{"entity": "attribute", "value": "chemicalClass"} is '
                f"[{name}](substances)?",
                'what family of [chemicals]{"entity": "attribute", "value": "chemicalClass"} is '
                f"[{name}](substances) in?",
                'what [chemical family]{"entity": "attribute", "value": "chemicalClass"} is '
                f"[{name}](substances)?",
                '[chemical type]{"entity": "attribute", "value": "chemicalClass"} of '
                f"[{name}](substances)",
                f"[{name}](substances) "
                '[chemical class]{"entity": "attribute", "value": "chemicalClass"}',
                f"[{name}](substances) is what "
                'type of [chemical]{"entity": "attribute", "value": "chemicalClass"}?',
                'what [class]{"entity": "attribute", "value": "psychoactiveClass"} is '
                f"[{name}](substances) in?",
                'what drug [class]{"entity": "attribute", "value": "psychoactiveClass"} is '
                f"[{name}](substances) in?",
                'what [family]{"entity": "attribute", "value": "psychoactiveClass"} of drugs is '
                f"[{name}](substances) in?",
                f"[{name}](substances) "
                '[class]{"entity": "attribute", "value": "psychoactiveClass"}',
                'what [kind of drug]{"entity": "attribute", "value": "psychoactiveClass"} is '
                f"[{name}](substances)?",
                f"is [{choice(doses)}]"
                '{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances) enough?",
                f"can i take [{choice(doses)}]"
                '{"entity": "attribute", "value": "roas"} of '
                f"[{name}](substances)",
            ]

            intents.append(choice(templates))
            if unlikely_chance > 3:
                mention_templates = [
                    f"[{name}](substances)?",
                    f"[{name}](substances) is what?",
                    'is [it](mention) safe to [mix]{"entity": "attribute", "value": "interactions"} with '
                    f"[{name}](substances)?",
                    'what substances [mix]{"entity": "attribute", "value": "interactions"} with [it](mention)',
                    'what does [it](mention) [interact]{"entity": "attribute", "value": "interactions"} with?',
                    'what [family]{"entity": "attribute", "value": "psychoactiveClass"} of drugs is [that](mention)in?',
                    'what is [its](mention) [class]{"entity": "attribute", "value": "psychoactiveClass"}',
                    '[chemical type]{"entity": "attribute", "value": "chemicalClass"} of [that](mention)?',
                    f"[{name}](substances) "
                    '[chemical class]{"entity": "attribute", "value": "chemicalClass"}',
                    f"is [{choice(doses)}]"
                    '{"entity": "attribute", "value": "roas"} of [that](mention) okay?',
                    f"is [{choice(doses)}]"
                    '{"entity": "attribute", "value": "roas"} of [it](mention) too much?',
                    f"is [{choice(doses)}]"
                    '{"entity": "attribute", "value": "roas"} of [it](mention) enough?',
                    'how [toxic]{"entity": "attribute", "value": "toxicity"} is [it](mention)',
                    'how [safe]{"entity": "attribute", "value": "toxicity"} is [that](mention)',
                ]

                intents.append(choice(mention_templates))

        return self.parse(intent_name="query_attributes", intent_list=intents)

    def combo_gen(self):
        combo_str = ""
        combo_str = "".join([combo_str, self.query_objects(), self.query_attributes()])
        return combo_str
