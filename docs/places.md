# Places

The Czech territorial units the app searches by, as RÚIAN defines them. Facts
only, each from a primary source listed at the end. Counts are from the ČÚZK
address dump of 2026-09-30. How a listing's text is matched to these units is
in [locating.md](locating.md).

## The units

| Kind | Czech | Example | Contained in | Boundary | Count |
|---|---|---|---|---|---|
| `kraj` | kraj | Plzeňský kraj | the state | yes | 14 |
| `okres` | okres | Domažlice | one kraj | yes | 76 |
| `obec` | obec | Plzeň, Kdyně | one okres | yes | 6,254 |
| `obvod` | obvod Prahy | Praha 7 | Praha | yes | 10 |
| `mestska_cast` | městská část, městský obvod (MOMC) | Praha 13, Plzeň 3 | one obec, and in Praha one obvod | yes | 142 |
| `cast_obce` | část obce | Holešovice | one obec | no | 15,106 |
| `ulice` | ulice | Přístavní | one obec | no | 85,997 |

- Praha has no okres. Its 10 obvody sit at okres level, and Praha is its own kraj.
- MOMC exist only in divided cities: Praha 57, Brno 29, Ostrava 23, Plzeň 10,
  Opava 9, Pardubice 8, Ústí nad Labem 4, Liberec 2. Obvody exist only in Praha.
- A část obce is a house-numbering unit, not an area. Its extent is the set of
  addresses numbered in it. A street is a line, not an area.
- Not modelled: region soudržnosti, ORP, POU and správní obvod are
  administrative tiers nobody searches by. Katastrální území is not in the
  address data, and in Praha it is the část obce.

## Containment

Every address belongs to exactly one unit of each kind. That makes the address
the one place where every containment question has a single answer.

- **Strict, one parent:** ulice and část obce lie in one obec, obec in one
  okres, okres in one kraj, MOMC in one obec, Praha's MOMC in one obvod.
- **Overlapping:** část obce and ulice cross MOMC and obvody, and ulice cross
  části obce. A part is "inside" a district only partly, through its addresses.
  - 23 of Praha's 112 části obce span more than one MOMC, 16 more than one obvod.
    Bubeneč has 1,035 addresses in Praha 6 and 370 in Praha 7.
  - Of Praha's streets, 459 cross a část obce, 196 a MOMC and 91 an obvod.
    Přístavní lies entirely in Holešovice, Praha 7.
  - Části obce cross MOMC in Brno, Plzeň, Pardubice, Opava and Ústí too.

## "Praha 7"

In an address, "Praha 7" is the **obvod**: the obec name is followed by the
obvod number, and the line before carries the část obce. "Praha 7 - Holešovice"
is obvod Praha 7 plus část obce Holešovice. Obvod Praha 7 consists of MČ Praha 7
and MČ Praha-Troja. The MČ Praha 11 to Praha 22 are not obvody, so their
addresses read "Praha 4", "Praha 5", "Praha 9" or "Praha 10".

## Codes

- Every unit has a RÚIAN code, unique and never reused once assigned.
- Codes are unique only within one kind: Praha's kraj code and obvod Praha 1's
  code are both 19. A place is therefore identified by its kind and its code.
- A rename keeps the code, and so does a move to another parent. A street is
  renamed by changing its record, never by cancelling and recreating it.

## Where the data comes from

- The address-point CSV (`OB_ADR`) carries code and name of the obec, MOMC,
  obvod, část obce and ulice for every address.
- The structural files (`strukt_ADR`) carry each address's okres and kraj codes.
- Both are published monthly by ČÚZK at
  https://nahlizenidokn.cuzk.gov.cz/StahniAdresniMistaRUIAN.aspx

## Sources

- Zákon č. 51/2020 Sb., o územně správním členění státu, and vyhláška
  č. 346/2020 Sb. (Praha's obvody): https://www.e-sbirka.cz/sb/2020/51
- Zákon č. 111/2009 Sb., o základních registrech (units, codes, § 29, § 31,
  § 32): https://www.e-sbirka.cz/sb/2009/111
- Zákon č. 128/2000 Sb., o obcích, and zákon č. 131/2000 Sb., o hlavním městě
  Praze (MOMC): https://www.e-sbirka.cz/sb/2000/128
- Vyhláška č. 359/2011 Sb. (address format, code formats):
  https://www.e-sbirka.cz/sb/2011/359
- ČÚZK, hierarchy of RÚIAN elements:
  https://cuzk.gov.cz/Uvod/Produkty-a-sluzby/RUIAN/2-Poskytovani-udaju-RUIAN-ISUI-VDP/Dopady-zmeny-zakona-c-51-2020-Sb/hierarchie-prvku-ruian-popis.aspx
- ČÚZK, rules for RÚIAN elements:
  https://cuzk.gov.cz/ruian/Editacni-agendovy-system-ISUI/Uzivatelske-postupy-v-ISUI/Pravidla_pro_zapis_prvku_v_ISUI.aspx

The full research behind this page, with every claim cited and the data
checks, is attached to issue #59.
