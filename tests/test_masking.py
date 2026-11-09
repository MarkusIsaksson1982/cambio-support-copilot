import pytest
from datetime import date
from copilot.core.masking import mask_text


class TestMasking:
    def test_personnummer_valid_12_masked(self):
        text = "Patienten har personnummer 811218-9876"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "811218-9876" not in masked
        assert "personnummer" in categories

    def test_personnummer_valid_10_masked(self):
        text = "Patienten har personnummer 100101-0006"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "100101-0006" not in masked
        assert "personnummer" in categories

    def test_personnummer_invalid_luhn_not_masked(self):
        text = "Patienten har personnummer 123412-1234"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "123412-1234" in masked

    def test_samordningsnummer_masked(self):
        text = "Patienten har samordningsnummer 020512-1234"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "020512-1234" not in masked or "personnummer" in categories

    def test_phone_masked(self):
        text = "Ring på 070-174 06 05"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "070-174 06 05" not in masked
        assert "telefon" in categories

    def test_email_masked(self):
        text = "Skicka till support@example.se"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "support@example.se" not in masked
        assert "epost" in categories

    def test_orgnr_masked(self):
        text = "Organisationsnummer 556677-8899"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "556677-8899" not in masked
        assert "organisationsnummer" in categories

    def test_name_anna_svensson_masked(self):
        text = "Anna Svensson ansöker om vård"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "Anna Svensson" not in masked
        assert "namn" in categories

    def test_name_erik_lindqvist_masked(self):
        text = "Erik Lindqvist ringde till oss"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "Erik Lindqvist" not in masked
        assert "namn" in categories

    def test_raw_never_appears_in_masked(self):
        text = "Patient Anna Svensson, pp 811218-9876, ring 070-174 06 05, stöd@example.se"
        masked, categories = mask_text(text, date(2026, 1, 1))
        assert "811218-9876" not in masked
        assert "Anna Svensson" not in masked
        assert "070-174 06 05" not in masked
        assert "stöd@example.se" not in masked

G001 = (
    "Titta i journalen för patient som inte kommer upp i sök. "
    "Hej, jag är ssk på Demoklinik Norr och behöver hjälp att titta i journalen "
    "för Astrid Holmgren 19121212-1212. Hon syns inte när jag söker på namn i EHR, "
    "men vi hade henne på UL igår."
)


class TestBareNameMasking:
    def test_g001_masks_name_and_valid_personnummer(self):
        masked, categories = mask_text(G001, date(2026, 11, 9))
        assert "Astrid Holmgren" not in masked
        assert "Astrid" not in masked
        assert "Holmgren" not in masked
        assert "19121212-1212" not in masked
        assert "[namn-maskat]" in masked
        assert "[personnummer-maskat]" in masked
        assert "Demoklinik Norr" in masked
        assert "namn" in categories
        assert "personnummer" in categories

    def test_name_before_invalid_personnummer_masks_name_only(self):
        text = "Exempelpatient: Tova Näckros, 810417-2846."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Tova Näckros" not in masked
        assert "810417-2846" in masked
        assert "[namn-maskat]" in masked
        assert "namn" in categories
        assert "personnummer" not in categories

    def test_testpatienten_cue_masks_following_name(self):
        text = "Det gäller testpatienten Astrid Holmgren i demokliniken Solbacken."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Astrid Holmgren" not in masked
        assert "Solbacken" in masked
        assert "namn" in categories

    def test_name_before_parenthesized_pnr(self):
        text = "Utskrift för patient Bengt Ohlsson (pnr 480722-1193) inför hemgång."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Bengt Ohlsson" not in masked
        assert "480722-1193" in masked
        assert "namn" in categories

    def test_space_separated_personnummer_shape_still_masks_name(self):
        text = "Remiss inkommen för Olof Svanberg 19621105 7743 men journalen öppnas inte."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Olof Svanberg" not in masked
        assert "19621105 7743" in masked
        assert "namn" in categories

    def test_isolated_given_name_signature_remains(self):
        text = (
            "Vi saknar labsvar i journalsystemet för Elsa Vinterberg, 870412-3456. "
            "/Mikael, avdelning 4"
        )
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "Elsa Vinterberg" not in masked
        assert "Mikael" in masked
        assert "870412-3456" in masked

    def test_clinic_phrase_not_treated_as_a_name(self):
        text = (
            "Systemförvaltare på Demoklinik Norr frågar om journalen för "
            "Linnea Berg 19850372-6614. Patienten har samordningsnummer."
        )
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "Demoklinik Norr" in masked
        assert "Linnea Berg" not in masked
        assert "19850372-6614" in masked

    def test_short_surname_before_id(self):
        text = "Anteckningen ligger på Gunnar Ek 540918-3392 men ska till rätt journal."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Gunnar Ek" not in masked
        assert "540918-3392" in masked
        assert "namn" in categories
