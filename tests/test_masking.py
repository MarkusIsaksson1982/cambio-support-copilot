import pytest
from datetime import date
from copilot.core.masking import find_organisationsnummer, find_personnummer, mask_text


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

    def test_slash_signature_given_name_is_masked(self):
        text = (
            "Vi saknar labsvar i journalsystemet för Elsa Vinterberg, 870412-3456. "
            "/Mikael, avdelning 4"
        )
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Elsa Vinterberg" not in masked
        assert "Mikael" not in masked
        assert "/[namn-maskat], avdelning 4" in masked
        assert "870412-3456" in masked
        assert "namn" in categories

    def test_bare_given_name_without_slash_or_surname_remains(self):
        text = (
            "Hej Mikael, journalsystemet visar inte labsvar för patienten. "
            "Kan ni kolla kön?"
        )
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "Mikael" in masked

    def test_slash_signature_with_surname_is_not_clipped(self):
        text = "Tack för hjälpen. /Astrid Holmgren, avdelning 4"
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Astrid" not in masked
        assert "Holmgren" not in masked
        assert "/[namn-maskat], avdelning 4" in masked
        assert "namn" in categories

    def test_slash_signature_double_given_name_and_surname(self):
        text = "Tack för hjälpen. /Anna Maria Svensson, avdelning 4"
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "Anna" not in masked
        assert "Maria" not in masked
        assert "Svensson" not in masked
        assert "/[namn-maskat], avdelning 4" in masked
        assert "namn" in categories

    def test_slash_signature_followed_by_colon(self):
        text = "Tack. /Mikael: prova igen i journalsystemet."
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "Mikael" not in masked
        assert "/[namn-maskat]: prova igen" in masked

    def test_slash_ul_is_not_treated_as_a_name(self):
        text = "Patienten syns inte i sök efter undersökningen /UL igår."
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "/UL" in masked

    def test_patient_letter_placeholder_is_masked(self):
        text = "Kollegan rapporterade att patient X med personnummer 240101-1234 väntar."
        masked, categories = mask_text(text, date(2026, 11, 9))
        assert "patient X" not in masked
        assert "patient [namn-maskat]" in masked
        assert "240101-1234" in masked
        assert "namn" in categories

    def test_patient_xray_is_not_a_placeholder(self):
        text = "Remissen för patient X-ray ligger kvar i kön."
        masked, _ = mask_text(text, date(2026, 11, 9))
        assert "patient X-ray" in masked

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


class TestGluedIdentifiers:
    """Name glued to an identifier used to survive the first (and only) scan.

    Title+name ran after personnummer. The PNR lookbehind saw the last letter
    of the name as wordish, so the number was not collected; replacing the name
    then left the digits in the clear (`patient Anna811218-9876` became
    `patient [namn-maskat]811218-9876`). Re-scanning until a fixpoint, and
    treating a mask token plus one following '-', '+' or space as a boundary,
    closes that gap.
    """

    today = date(2026, 1, 1)

    def _assert_gone(self, raw: str, masked: str, *fragments: str) -> None:
        for fragment in fragments:
            assert fragment not in masked, (raw, masked, fragment)

    def test_glued_name_and_personnummer_without_separator(self):
        raw = "patient Anna811218-9876"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "811218-9876", "8112189876", "Anna")
        assert masked == "patient [namn-maskat][personnummer-maskat]"
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_name_and_personnummer_with_hyphen(self):
        raw = "patient Anna-811218-9876"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "811218-9876", "8112189876", "Anna")
        assert masked == "patient [namn-maskat]-[personnummer-maskat]"
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_name_and_10_digit_personnummer_no_hyphen(self):
        raw = "patient Anna8112189876"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "8112189876", "Anna")
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_name_and_12_digit_personnummer_with_hyphen(self):
        raw = "patient Anna19870312-4514"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "19870312-4514", "198703124514", "870312-4514", "Anna")
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_name_and_12_digit_personnummer_no_hyphen(self):
        raw = "patient Anna198703124514"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "198703124514", "19870312-4514", "Anna")
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_title_lastname_and_century_prefixed_personnummer(self):
        raw = "dr Lindqvist198112189876"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "198112189876", "19811218-9876", "811218-9876", "Lindqvist")
        assert "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_glued_name_and_orgnr_with_and_without_hyphen(self):
        for raw, leftover_hyphen in (
            ("patient Anna556677-8899", False),
            ("patient Anna-556677-8899", True),
            ("patient Anna5566778899", False),
        ):
            masked, categories = mask_text(raw, self.today)
            self._assert_gone(raw, masked, "556677-8899", "5566778899", "Anna")
            assert "organisationsnummer" in categories and "namn" in categories
            assert find_organisationsnummer(masked) == []
            if leftover_hyphen:
                assert masked == "patient [namn-maskat]-[organisationsnummer-maskat]"
            else:
                assert masked == "patient [namn-maskat][organisationsnummer-maskat]"

    def test_email_adjacent_to_glued_name_and_personnummer(self):
        raw = "patient Anna811218-9876 kontakta foo@example.se"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(
            raw, masked,
            "811218-9876", "8112189876", "Anna",
            "foo@example.se",
        )
        assert masked == (
            "patient [namn-maskat][personnummer-maskat] kontakta [epost-maskat]"
        )
        assert "epost" in categories and "personnummer" in categories and "namn" in categories
        assert find_personnummer(masked, self.today) == []

    def test_name_glued_to_email_is_swallowed_as_email(self):
        # PRIORITET puts e-mail first, so Annafoo@example.se is one address.
        raw = "patient Annafoo@example.se"
        masked, categories = mask_text(raw, self.today)
        self._assert_gone(raw, masked, "Annafoo@example.se", "foo@example.se", "Anna")
        assert masked == "patient [epost-maskat]"
        assert categories == ["epost"]

    def test_invalid_luhn_glued_to_name_stays_visible(self):
        raw = "patient Anna123412-1234"
        masked, categories = mask_text(raw, self.today)
        assert "Anna" not in masked
        assert "123412-1234" in masked
        assert "namn" in categories
        assert "personnummer" not in categories
        assert find_personnummer(masked, self.today) == []
