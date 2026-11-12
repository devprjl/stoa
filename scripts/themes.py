import re

THEMES = [
    (r"death|die[sd]?|dying|dead|mortal\w*|grave|tomb", ["skull", "vanitas", "memento mori", "tomb", "death"]),
    (r"time|hour|moment|years?|age|eternit\w+|forever", ["hourglass", "clock", "sundial", "calendar", "old man"]),
    (r"war|battle|soldiers?|army|fight\w*|conquer\w*", ["armor", "battle", "helmet", "soldier", "cavalry"]),
    (r"swords?|blade|steel", ["sword", "dagger", "saber", "rapier"]),
    (r"sea|ocean|waves?|ships?|sail\w*|storm|tide", ["ship", "storm at sea", "wave", "sailing", "shipwreck"]),
    (r"wisdom|wise|knowledge|learn\w*|teach\w*|stud\w+|philosoph\w+", ["philosopher", "scholar", "owl", "reading", "library"]),
    (r"books?|read\w*|writ\w+|words?|poet\w*|letters?", ["book", "writer", "inkwell", "scribe", "reading woman"]),
    (r"love|lover?s?|beloved|kiss", ["cupid", "lovers", "venus", "embrace", "heart"]),
    (r"night|moon|stars?|sky|heavens?", ["moon", "night", "stars", "astronomer", "celestial"]),
    (r"sun|dawn|morning|light|bright", ["sunrise", "sun", "lamp", "candle", "apollo"]),
    (r"dark\w*|shadow|blind", ["night scene", "shadow", "nocturne", "cave"]),
    (r"fire|flames?|burn\w*|ashes", ["fire", "flame", "torch", "volcano", "forge"]),
    (r"kings?|queens?|crown|throne|emperor|ruler?s?|power", ["king", "crown", "emperor", "throne", "scepter"]),
    (r"gods?|divine|heaven|faith|pray\w*|holy|sacred", ["angel", "deity", "temple", "saint", "altar"]),
    (r"nature|trees?|forest|leaves|flowers?|garden|spring", ["tree", "forest", "flowers", "garden", "landscape"]),
    (r"mountains?|rock|stone|hill", ["mountain", "rocks", "cliff", "alps"]),
    (r"rivers?|water|rain|stream|flow", ["river", "waterfall", "bridge", "fountain"]),
    (r"road|path|journey|travel\w*|wander\w*|way", ["traveler", "road", "pilgrim", "horse and rider", "wanderer"]),
    (r"home|house|door|walls?|city|cities", ["house", "doorway", "city view", "street", "village"]),
    (r"freedom|free|liberty|chains?|slaves?|prison\w*", ["liberty", "prisoner", "chains", "broken chain", "bird in flight"]),
    (r"truth|lies?|honest\w*|deceiv\w*|masks?", ["mask", "mirror", "justice", "allegory of truth"]),
    (r"justice|law|judge\w*|right|wrong", ["justice", "scales", "judge", "tribunal"]),
    (r"fear|afraid|terror|danger|monsters?", ["monster", "demon", "dragon", "nightmare", "medusa"]),
    (r"courage|brave\w*|hero\w*|valor|glory|victor\w*", ["hercules", "warrior", "victory", "knight", "laurel"]),
    (r"hope|dreams?|sleep\w*|wish", ["sleeping figure", "dream", "allegory of hope", "anchor"]),
    (r"sorrow|grief|tears|weep\w*|pain|suffer\w*|sad\w*", ["mourning", "weeping", "melancholy", "pieta"]),
    (r"happiness|happy|joy|laugh\w*|smile|pleasure", ["dancing", "feast", "laughing", "musicians", "bacchus"]),
    (r"friends?|friendship|together|brothers?|companions?", ["two men", "companions", "conversation", "handshake"]),
    (r"alone|solitude|lonel\w+|silence|quiet", ["hermit", "solitary figure", "monk", "empty landscape"]),
    (r"mind|thought|think\w*|reason|idea", ["thinker", "head study", "portrait of a man", "bust"]),
    (r"soul|spirit|heart|self", ["psyche", "portrait", "self-portrait", "figure study"]),
    (r"men|man|human\w*|people|mankind|world", ["crowd", "figure", "atlas", "globe", "portrait of a man"]),
    (r"women|woman|mother|daughter|wife|girl", ["portrait of a woman", "mother and child", "woman"]),
    (r"child\w*|youth|young|boy|father|son", ["child", "youth", "father and son", "boy"]),
    (r"old|elders?|aged|ancient", ["old man", "old woman", "ruins", "elder"]),
    (r"work|labou?r|craft|build\w*|make|made|hands?", ["blacksmith", "workshop", "hands", "tools", "craftsman"]),
    (r"money|gold|rich\w*|wealth|poor|poverty|fortune", ["coins", "money changer", "treasure", "beggar", "fortuna"]),
    (r"music|song|sing\w*|dance", ["lute", "musician", "violin", "singer", "dancer"]),
    (r"art|beauty|beautiful|paint\w*", ["venus", "artist in studio", "muse", "still life"]),
    (r"animals?|beasts?|wolf|wolves|lions?|horses?|birds?|dogs?", ["lion", "wolf", "horse", "eagle", "hound"]),
    (r"fools?|folly|mad\w*|stupid\w*", ["jester", "fool", "folly", "caricature"]),
    (r"fate|destiny|fortune|chance|luck", ["fortuna", "wheel of fortune", "dice", "fates", "tarot"]),
    (r"evil|sin|devil|hell|wicked", ["devil", "hell", "temptation", "serpent"]),
    (r"good|virtue|noble|honou?r|duty", ["allegory of virtue", "knight", "minerva", "saint george"]),
    (r"change|begin\w*|end|new|future|past|history|memor\w+", ["ruins", "janus", "phoenix", "chronos", "antiquity"]),
    (r"machines?|science|stars|universe|space|earth", ["astrolabe", "globe", "telescope", "armillary sphere", "scientific instrument"]),
    (r"anger|rage|hate|hatred|revenge|enem\w+", ["fury", "combat", "duel", "mars", "nemesis"]),
    (r"peace|calm|rest|still", ["dove", "calm sea", "resting figure", "olive branch", "pastoral"]),
]

DEFAULTS = {
    "philosophy": ["philosopher", "bust of a man", "greek sculpture", "roman portrait", "scholar", "sage", "antique head", "stoic"],
    "literature": ["poet", "reading", "writer", "book illustration", "muse", "portrait engraving", "author"],
    "game": ["knight", "armor", "sword", "dragon", "samurai", "helmet", "shield", "warrior", "castle", "netsuke"],
    "movie": ["theater", "mask", "actor", "stage", "portrait", "night scene", "city view", "kabuki"],
    "tv": ["theater", "actor", "mask", "city view", "portrait"],
}

STOP = re.compile(r"[a-z']+")


def terms_for(quote, seed):
    words = set(STOP.findall(quote["text"].lower()))
    matched = []
    for pattern, terms in THEMES:
        if any(re.fullmatch(pattern, word) for word in words):
            matched.append(terms[seed % len(terms)])
            matched.append(terms[(seed // 7 + 1) % len(terms)])
    order = []
    if quote["category"] in ("philosophy", "literature") and quote.get("author") and seed % 3 == 0:
        order.append(quote["author"])
    rotate = seed % len(matched) if matched else 0
    order += matched[rotate:] + matched[:rotate]
    defaults = DEFAULTS[quote["category"]]
    rotate = seed % len(defaults)
    order += defaults[rotate:] + defaults[:rotate]
    seen, unique = set(), []
    for term in order:
        if term not in seen:
            seen.add(term)
            unique.append(term)
    return unique
