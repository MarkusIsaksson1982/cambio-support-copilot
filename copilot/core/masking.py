"""Mask PII (personnummer, organisationsnummer, names, phone, e-mail) before sending text to the LLM.

Dataskydd: identifierare upptäcks och maskeras FÖRE reglerna, FÖRE model_fn och i
alla utdata (beslut, trace, granskningskö, audit, filer).

Ärendetexten är sjukvårdsdata enligt Patientdatalagen (2008:355). Personnummer,
namn, telefon, e-post och andra direkta identifierare ska aldrig lämna processen i
klartext - inte till regelmotorn, inte till modellen, inte till en fil.

Maskningen är ett HINDER, inte en lösning: orden är avsiktligt försiktiga, fångar
inte diagnoskoder eller fritext som råkar beskriva en person, och en fritextmaskering
kan övermaskera ett vanligt ord. Riktig användning kräver dessutom gallring,
åtkomstlogg och kryptering - se README.
"""
from __future__ import annotations

import re
from datetime import date

MASK = "[personnummer-maskat]"
NAMN_MASK = "[namn-maskat]"
TELEFON_MASK = "[telefon-maskat]"
EPOST_MASK = "[epost-maskat]"
IDENT_MASK = "[identifierare-maskat]"
ORGNR_MASK = "[organisationsnummer-maskat]"

MASKER = {"personnummer": MASK, "namn": NAMN_MASK, "telefon": TELEFON_MASK,
          "epost": EPOST_MASK, "identifierare": IDENT_MASK,
          "organisationsnummer": ORGNR_MASK}

# Ordning = prioritet. En kandidat som överlappar en redan accepterad träff
# hoppas över, så att t.ex. ett tioställigt telefonnummer inte maskas som
# personnummer. E-post går först eftersom den kan innehålla både siffror och @.
PRIORITET = ("epost", "telefon", "personnummer", "organisationsnummer", "identifierare", "namn")

# Syntetiska namn ur det fiktiva exempelmaterialet. Riktiga namn ska inte ligga i
# koden; listan är ett prov på hur namnlista + heuristik kan kombineras.
SYNTHETISKA_NAMN = ("Anna Svensson", "Erik Lindqvist", "Karin Ekström", "Lars Öberg",
                    "Fatima Hassan", "Bo Ek")

# 12 (YYYYMMDD-XXXX) eller 10 (YYMMDD-XXXX) siffror, med bindestreck, plustecken
# eller utan avgränsare. Avgränsarna skyddar mot att greda in i ett längre tal.
# 12 siffror bär århundradet; 10 tolkas med avgränsaren ('-' = under 100 år,
# '+' = 100 år eller mer) och kontrollsumman (Luhn) räknas på tio siffror.
_PERSONNUMMER = re.compile(r"(?<![\w-])(\d{4}|\d{2})(\d{2})(\d{2})([-+ ]?)(\d{4})(?![\w-])")
# Organisationsnummer (Swedish organisation number): NNNNNN-NNNN, optionally prefixed "16"
# (12-digit form used by Skatteverket). The third digit is 2 or higher, so it can never be a
# valid personnummer month; the tenth digit is a Luhn check digit over the ten digits.
_ORGNR = re.compile(r"(?<![\w-])(?:16)?(\d{2}[2-9]\d{3})-?(\d{4})(?![\w-])")
_EPOST = re.compile(r"(?<![\w-])[\w.+-]+(?:@|\(at\))[\w-]+(?:\.[\w-]+)+(?![\w-])", re.IGNORECASE)
# Svenska telefonnummer: 070-174 06 05, 0701740605, +46 70 174 06 05 samt fasta nummer med riktnummer (08-, 0xx-).
# Områdesnumret måste se ut som ett svenskt område (07x mobil, 08/031/090 fast), och
# abonnentdelen måste gruppera sig som ett nummer. Det breda mönster som fanns
# tidigare tog varje siffersträng med tillräckligt många grupper, och fångade därför
# datum, belopp och ordningsnummer.
_TELEFON = re.compile(
    r"(?<![\w-])(?:\(\s*\+?46\s*\)[\s.-]?|\(\s*0|\+46[\s.-]?|0046[\s.-]?|0)"
    r"(?:7[0-9]\)?[\s.-]?\d{3}[\s.-]?\d{2}[\s.-]?\d{2}"            # mobil: 070-174 06 05 / (070) 174 06 05
    r"|[1-9]\d{0,2}\)?[\s.-]?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2})"  # fast: riktnummer + abonnentnummer
    r"(?![\w-])")
# Andra direkta identifierare: patient-/dossier-/ärendenummer och liknande.
_IDENT = re.compile(
    r"(?<![\w-])(?:(?:patient|dossier|ärende|avdelning|vårdenhet|journal)"
    r"\s*-?\s*(?:nummer|id|nr|no)|journalnummer|hsa[\s-]?id)"
    r"\s*[:#]?\s*[A-Za-z0-9][A-Za-z0-9_-]{3,}",
    re.IGNORECASE)
# Titel eller roll före ett namn: "dr Lindqvist", "patient Anna Svensson".
_TITLAR = (r"dr|docent|professor|överläkare|läkare|sjuksköterska|sjuksköterskor|"
           r"receptionist|fru|herr|barn|pojkar|"
           # Vanliga rollförkortningar i svensk vård (ssk, usk, böl, mas, dsk).
           r"ssk|usk|böl|mas|dsk")
_NAMNKUPPLETER = (r"patient|patienten|testpatienten|övningspatienten|"
                  r"exempelpatient|exempelnamn|exempelpersonen|"
                  r"pojken|flickan|granskare|granskat\s+av|"
                  r"inrapporterad\s+av|ansvarig")
_EFTERNAMN = r"[A-ZÅÄÖÉ][a-zåäöé]+(?:-[A-ZÅÄÖÉa-zåäöé]+)?"
# Optional colon after the cue: "Exempelpatient: Tova Näckros".
_TITEL_NAMN = re.compile(r"(?<![\w-])(?i:" + _TITLAR + r"|" + _NAMNKUPPLETER + r")\.?:?\s+"
                         r"(" + _EFTERNAMN + r"(?:\s+" + _EFTERNAMN + r")?)")
# Optional Swedish genitive -s/-es on the listed name (Anna Svenssons).
_NAMNLISTA = re.compile(r"(?<![\w-])(?:"
                        + "|".join(re.escape(n) for n in sorted(SYNTHETISKA_NAMN, key=len,
                                                                reverse=True))
                        + r")(?:e?s)?(?![\w-])", re.IGNORECASE)
# Bare Swedish name immediately before a personnummer-shaped token, valid or not.
# The name is masked; Luhn-invalid numbers stay visible on purpose.
_NAME_WORD = r"[A-ZÅÄÖÉ][a-zåäöé]+(?:-[A-ZÅÄÖÉ][a-zåäöé]+)?"
_PNR_SHAPE = r"\d{6,8}[-+ ]?\d{4}"
_NAMN_FORE_ID = re.compile(
    r"(?<![\w-])(" + _NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){1,2}),?\s+"
    r"(?:\(\s*(?:pnr|personnummer)\s+|(?:pnr|personnummer)\s+)?"
    + _PNR_SHAPE)
_NAME_TOKEN = re.compile(_NAME_WORD)
# Staff signature "/Mikael", "/Astrid Holmgren" or "/Anna Maria Svensson".
# Gazetteer-only on the first given name so "/UL" stays put. Up to two
# following name words avoid cutting through a longer name. Trailing
# comma, semicolon, colon or period is allowed; "patient X-ray" is not
# handled here.
_SIGNATUR_NAMN = re.compile(
    r"(?<![\w-])\/(" + _NAME_WORD + r"(?:\s+" + _NAME_WORD + r"){0,2})(?=[,;:.!?\s]|$)")
# Anonymization placeholder "patient X" / "patienten X". "patient X-ray" does not match.
_PATIENT_PLATSHALLARE = re.compile(
    r"(?<![\w-])(?i:patient(?:en)?)\.?:?\s+([A-ZÅÄÖÉ])(?![\w-])")
# Common Swedish given names plus those used in the synthetic tickets. This is a
# heuristic gazetteer, not a complete civil register. Matching is casefold().
_GIVEN_NAMES = frozenset("""
    agnes agneta agneta alexander alfred alice alma alva amanda anders andreas
    anette anja ann anna anne anneli annika anton arvid astrid axel barbro
    beatrice bengt berit birgitta björn bo britta camilla carina carl carola
    cecilia charlotte christel christian christoffer dagmar daniel david dennis
    disa ebba edit edith einar elias elin elina elisabeth elise ella ellen
    ellinor elsa elsie emelie emilia emil emma emmy erik erika ernest esther
    eva evelina felicia filip filippa fredrik freja frida gun gunilla gunnar
    gustav göran hans hanna harald helena helene henrik henrietta hilda hilma
    hugo ida inga ingalill ingemar inger ingrid isabella isak ivar jacob jakob
    jan janne jasmin jens jesper joakim joel johan johanna john jon jonas
    jonathan josef josefin josefine julia julianna karl karin karolina kent
    kim klara kristian kristin kristina lars lena leif lennart lilian lina
    linda linn linnea linnéa lisbeth lise lotta lotte louise love lovisa lucas
    ludvig lydia lykke madeleine maja malin malte marcel marcus margareta
    margit maria mariana marie marika marina marta martin martina matilda
    mats mattias max melissa mia michael mikael mira miriam moa mohammad
    mohammed monica monika märta nadja natalie nathalie nicklas niklas nilla
    nils noah noomi nora oliver olivia olof olov oscar oskar otto patricia
    patrik paul per pernilla peter petra petter pia ragnar rebecca regina
    richard rickard robert robin roger roland ronja rosa rut ruth saga sara
    selma signe sigrid simon sixten sofia sofie sonja stefan stella stina
    susanne sven sören tage thea theodor therese thomas tobias toma tove tova
    tuva ulla ulrika urban valter vanja vera veronica victor viktor viktor
    vilhelm vilma vilmer vincent wilma william ylva yvonne åke åsa älva
    östen fatima tova vilmer carina elsa nils bengt märta
    linnea olof gunnar johan
""".split())
_SURNAME_STOP = frozenset("""
    norr syd öst ost väst vast sverige sveriges support systemet system
    portal portalen klinik kliniken demoklinik demo ab as kb ul ehr it id
    pin json http api stockholm göteborg goteborg malmö malmo uppsala
    linköping linkoping örebro orebro västerås vasteras helsingborg umeå
    umea
""".split())


def _luhn_ok(siffror: str) -> bool:
    """Luhn-kontroll (mod 10). Räknas på de tio siffrorna: YY + MM + DD + NNN + C."""
    total = 0
    for i, ch in enumerate(reversed(siffror)):
        siffra = int(ch)
        if i % 2:
            siffra = siffra * 2 - 9 if siffra > 4 else siffra * 2
        total += siffra
    return total % 10 == 0


def _år_från_två(år2: str, avgränsare: str, idag: date) -> int:
    """Årtalet i ett tioårigt personnummer - en tolkning, inte ett fakta.

    Två siffror bär inte med sig århundradet: '+' betyder 100 år eller mer
    (föregående århundrade), '-' och saknad avgränsare betyder yngre än 100 år,
    alltså det närmaste årtal som inte ligger i framtiden. Referensdatumet skickas
    in, så att ett test inte flyttar med sig när kalendern gör det.
    """
    århundra = (idag.year // 100 - (1 if avgränsare == "+" else 0)) * 100
    ar = århundra + int(år2)
    return ar - 100 if ar > idag.year else ar


def _datum_ok(ar: int, manad: int, dag: int, idag: date) -> bool:
    """Sparar ogiltiga datum så att ett ordningsnummer inte maskas som personnummer."""
    if not 1800 <= ar <= idag.year + 1 or not 1 <= manad <= 12:
        return False
    try:
        date(ar, manad, dag)
    except ValueError:
        return False
    return True


def _giltigt_personnummer(träff, idag: date) -> bool:
    """Datum och Luhn på en träff: 12 siffror bär århundradet, 10 tolkas med avgränsaren.

    Samordningsnummer har dagen +60 (61-91), så 850372-0016 är 1985-03-12. Luhn räknas
    på siffrorna som de står, alltså med den skrivna dagen.
    """
    år, manad, dag, avgränsare, kontroll = träff.groups()
    ar = int(år) if len(år) == 4 else _år_från_två(år, avgränsare, idag)
    dagnummer = int(dag)
    if not _datum_ok(ar, int(manad), dagnummer - 60 if 61 <= dagnummer <= 91 else dagnummer,
                     idag):
        return False
    return _luhn_ok(år[-2:] + manad + dag + kontroll)



_PATIENT_ID_CONTEXT = re.compile(
    r"journal|patient|personnummer|samordningsnummer|\bpnr\b|vårdrelation|öppna journal",
    re.IGNORECASE)


def find_unverified_personnummer_shapes(text: str, idag: date | None = None) -> list[str]:
    """Date-plausible personnummer/samordning shapes that fail Luhn.

    Used for handoff only. Masking stays Luhn-strict so the demo can show the gap.
    Requires patient/journal context so ticket ids and build stamps are not treated as PII.
    """
    if not isinstance(text, str) or not _PATIENT_ID_CONTEXT.search(text):
        return []
    idag = idag or date.today()
    out = []
    for m in _PERSONNUMMER.finditer(text):
        if _giltigt_personnummer(m, idag):
            continue
        year, month, day, sep, _check = m.groups()
        ar = int(year) if len(year) == 4 else _år_från_två(year, sep, idag)
        day_n = int(day)
        real_day = day_n - 60 if 61 <= day_n <= 91 else day_n
        if _datum_ok(ar, int(month), real_day, idag):
            out.append(m.group(0))
    return out


def find_personnummer(text: str, idag: date | None = None) -> list[str]:
    """Alla personnummer i texten, i tur ordning.

    `idag` är referensdatumet för århundradet i tioåriget form (default: dagens datum),
    och skickas in utifrån så att testerna blir oberoende av kalendern.
    """
    idag = idag or date.today()
    return [m.group(0) for m in _PERSONNUMMER.finditer(text)
            if _giltigt_personnummer(m, idag)]


def _spann_personnummer(text, idag: date | None = None):
    idag = idag or date.today()
    for m in _PERSONNUMMER.finditer(text):
        if _giltigt_personnummer(m, idag):
            yield m.start(), m.end(), "personnummer", MASK


def _giltigt_organisationsnummer(träff) -> bool:
    return _luhn_ok(träff.group(1) + träff.group(2))


def find_organisationsnummer(text: str) -> list[str]:
    """Detect Swedish organisationsnummer (org number / company ID) with Luhn validation.

    Alla organisationsnummer i texten, i tur ordning. Både 556677-8899-formen och den
    tolvsiffriga 16-formen godtas; tredje siffran måste vara minst 2 och kontrollsiffran
    stämma (Luhn), annars är det bara ett tal.
    """
    return [m.group(0) for m in _ORGNR.finditer(text) if _giltigt_organisationsnummer(m)]


def _spann_organisationsnummer(text):
    for m in _ORGNR.finditer(text):
        if _giltigt_organisationsnummer(m):
            yield m.start(), m.end(), "organisationsnummer", ORGNR_MASK


def _spann_enkel(text, mönster, kategori, ersättning):
    for m in mönster.finditer(text):
        yield m.start(), m.end(), kategori, ersättning


def _spann_titel_namn(text):
    # Bara namnet maskas: titeln ("dr", "patient") är roll, inte identifierare.
    for m in _TITEL_NAMN.finditer(text):
        yield m.start(1), m.end(1), "namn", NAMN_MASK


def _spann_namn_fore_id(text):
    """Mask a Firstname Lastname that sits immediately before a personnummer shape."""
    for m in _NAMN_FORE_ID.finditer(text):
        yield m.start(1), m.end(1), "namn", NAMN_MASK


def _spann_signatur_namn(text):
    """Mask a gazetteer name after a staff-style slash signature ('/Mikael')."""
    for m in _SIGNATUR_NAMN.finditer(text):
        parts = m.group(1).split()
        if parts[0].casefold() not in _GIVEN_NAMES:
            continue
        if len(parts) == 3 and parts[1].casefold() not in _GIVEN_NAMES:
            parts = parts[:2]
        if len(parts) >= 2:
            last = parts[-1].casefold()
            if last in _SURNAME_STOP or last.rstrip("s") in _SURNAME_STOP:
                parts = parts[:-1]
        span = " ".join(parts)
        yield m.start(1), m.start(1) + len(span), "namn", NAMN_MASK


def _spann_patient_platshallare(text):
    """Mask a single capital letter used as a patient placeholder ('patient X')."""
    for m in _PATIENT_PLATSHALLARE.finditer(text):
        yield m.start(1), m.end(1), "namn", NAMN_MASK


def _spann_svenska_namnpar(text):
    """Mask given-name + surname pairs when the ticket already looks like patient data.

    Clinic phrases ("Demoklinik Norr") are left alone. Slash signatures and the
    single-letter placeholder "patient X" are handled separately. This is a
    heuristic: it will miss unusual names and can over-mask a rare given-name +
    ordinary-word pair.
    """
    if not isinstance(text, str) or not _PATIENT_ID_CONTEXT.search(text):
        return
    tokens = list(_NAME_TOKEN.finditer(text))
    i = 0
    while i < len(tokens) - 1:
        first, nxt = tokens[i], tokens[i + 1]
        if not text[first.end():nxt.start()].isspace():
            i += 1
            continue
        last = nxt
        consumed = 2
        if (i + 2 < len(tokens)
                and text[nxt.end():tokens[i + 2].start()].isspace()
                and first.group(0).casefold() in _GIVEN_NAMES
                and nxt.group(0).casefold() in _GIVEN_NAMES):
            last = tokens[i + 2]
            consumed = 3
        if first.group(0).casefold() not in _GIVEN_NAMES:
            i += 1
            continue
        last_key = last.group(0).casefold()
        if last_key in _SURNAME_STOP or last_key.rstrip("s") in _SURNAME_STOP:
            i += 1
            continue
        yield first.start(), last.end(), "namn", NAMN_MASK
        i += consumed


def _kandidater(text, idag: date | None = None):
    """Identifierarkandidater i prioritetsordning - se PRIORITET."""
    return (_spann_enkel(text, _EPOST, "epost", EPOST_MASK),
            _spann_enkel(text, _TELEFON, "telefon", TELEFON_MASK),
            _spann_personnummer(text, idag),
            _spann_organisationsnummer(text),
            _spann_enkel(text, _IDENT, "identifierare", IDENT_MASK),
            _spann_titel_namn(text),
            _spann_patient_platshallare(text),
            _spann_namn_fore_id(text),
            _spann_svenska_namnpar(text),
            _spann_signatur_namn(text),
            _spann_enkel(text, _NAMNLISTA, "namn", NAMN_MASK))


def _krock(start: int, stop: int, träffar: list[tuple]) -> bool:
    """True om [start, stop) överlappar en redan accepterad träff."""
    return any(start < t[1] and stop > t[0] for t in träffar)


# Tokens this module writes. Built from MASKER so a new category stays in sync.
_MASK_TOKEN = re.compile("|".join(re.escape(token) for token in MASKER.values()))
# After a token, a single '-', '+' or space still blocks identifier lookbehinds
# because those characters count as wordish in the identifier lookbehind. Treat that one glue character as
# a boundary too, so a second pass can see a number glued on with a hyphen.
_GLUE_AFTER_TOKEN = frozenset("-+ ")


def _soften_masked_boundaries(text: str) -> str:
    """Replace already-written mask tokens (and one following glue char) with spaces.

    Same length as `text`, so span offsets from the scanners still apply to the
    original string. A first pass that masks a name glued to a personnummer,
    e.g. `patient Anna811218-9876` -> `patient [namn-maskat]811218-9876`, leaves
    the digits visible: the original wordish lookbehind failed against the
    last letter of the name. After replacement `]` is not wordish, so a second
    pass would find the number — except the hyphenated form
    `patient Anna-811218-9876` becomes `[namn-maskat]-811218-9876`, and `-`
    still blocks the lookbehind. Softening the token and that one glue
    character makes the identifier scanners treat the mask as a boundary
    without changing any other text.
    """
    if "[" not in text:
        return text
    chars = list(text)
    for match in _MASK_TOKEN.finditer(text):
        for i in range(match.start(), match.end()):
            chars[i] = " "
        glue_at = match.end()
        if glue_at < len(text) and text[glue_at] in _GLUE_AFTER_TOKEN:
            chars[glue_at] = " "
    return "".join(chars)


def _mask_once(text: str, idag: date) -> tuple[str, list[str]]:
    """One scan/replace pass. Scanners run on a softened view; edits apply to `text`."""
    view = _soften_masked_boundaries(text)
    träffar: list[tuple[int, int, str, str]] = []
    for kandidater in _kandidater(view, idag):
        for start, stopp, kategori, ersättning in kandidater:
            if _krock(start, stopp, träffar):
                continue
            träffar.append((start, stopp, kategori, ersättning))
    if not träffar:
        return text, []
    delar = []
    förra = 0
    for start, stopp, _kategori, ersättning in sorted(träffar):
        delar.append(text[förra:start])
        delar.append(ersättning)
        förra = stopp
    delar.append(text[förra:])
    kategorier = sorted({t[2] for t in träffar}, key=PRIORITET.index)
    return "".join(delar), kategorier


def mask_text(text, idag: date | None = None) -> tuple[str, list[str]]:
    """Maskera alla identifierare. Returnera (maskad text, kategorier i prioritetsordning).

    Kategorierna (t.ex. ["personnummer", "namn"]) går vidare till trace, så att det
    går att se att maskningen skett - utan att de råa värdena någonstans skrivs ut.
    `idag` är referensdatumet för århundradet i tioåriget personnummer.

    Re-scan until a fixpoint. A name glued to a personnummer is invisible to the
    identifier lookbehind on the first pass (the last letter of the name is
    wordish). After the name is replaced, a later pass sees the number. Each
    changing pass replaces at least one raw span, so `len(text) + 1` is a hard
    upper bound; real inputs settle in two passes.
    """
    if not isinstance(text, str):
        return text, []
    idag = idag or date.today()
    collected: set[str] = set()
    current = text
    for _ in range(len(text) + 1):
        masked, categories = _mask_once(current, idag)
        collected.update(categories)
        if masked == current:
            break
        current = masked
    return current, sorted(collected, key=PRIORITET.index)


def mask_note(text: str, idag: date | None = None) -> str:
    """Maskera en fritext (granskningsnotat) - används innan den sparas i audit."""
    return mask_text(text if isinstance(text, str) else "", idag)[0]


def sanitize(value, idag: date | None = None):
    """Maskera identifierare i alla strängar i ett beslut (djupt, utan att skapa cykler)."""
    if isinstance(value, str):
        return mask_text(value, idag)[0]
    if isinstance(value, dict):
        return {k: sanitize(v, idag) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v, idag) for v in value]
    return value