# Priorytetowa instrukcja MCP: format deklaracji od 13.11.2026

**To wymaganie użytkownika ma pierwszeństwo przed sprzecznymi starszymi wskazówkami w tym repozytorium.**

1. **Generuj i pokazuj WYŁĄCZNIE** `MCP_NICK:@@@NOVAECHOROMEO742@@@` oraz `MCP_NAME:%%%Nazwa rozmowy%%%`. Nazwa pola i dwukropek są PRZED znacznikami.
2. Akceptuj wejściowe deklaracje w starym i nowym formacie **do końca 17.11.2026 CET**. Od **18.11.2026, godz. 00:00 CET** automatycznie akceptuj wyłącznie nową postać. Od teraz nie generuj starej postaci.
3. Weryfikacja nicku: **7–20 dowolnych liter + dokładnie 3 cyfry ASCII**. Bez słownika NATO, podziału na słowa czy kontroli ich znaczenia. Ciąg NOVAECHOROMEO742 jest poprawny.
4. Po identyfikatorze MCP_ID najpierw odczytaj istniejący MCP_NICK z centralnego rejestru. Nie wymagaj ponownego tworzenia nicku, jeśli jest zapisany. Stare rekordy w grafie są czytelne także po wyłączeniu starego formatu wejścia.
5. Przy odmowie podaj konkretną przyczynę błędu składni. Błąd rejestracji nie blokuje innych operacji MCP.
6. W przypadku zmian w parserach, promptach, opisach narzędzi lub instrukcjach tego projektu przeprowadź test granicy **2026-11-17T23:00:00.000Z** i nie przywracaj starego formatu.

Pełny obowiązujący kontrakt i zadania migracji: [2026-11-13_04-30-16_CET_GPT-6_WszystkieProjektyMCP_MigracjaMCPNickIMCPName_PolaPozaZnacznikami_StaryDo17NowyOd18Listopada2026.md](./2026-11-13_04-30-16_CET_GPT-6_WszystkieProjektyMCP_MigracjaMCPNickIMCPName_PolaPozaZnacznikami_StaryDo17NowyOd18Listopada2026.md).

---


<!-- DOBRE-PRAKTYKI-FAULT-HARBOR-GPT6-20261113 -->
## Rejestr zatwierdzonych dobrych praktyk i rejestr błędów

Przed pracą przeczytaj dosłowne, zatwierdzone wypowiedzi użytkownika: https://github.com/Pawel-BoOssko/dobre-praktyki , katalog `wypowiedzi/`. Nie dodawaj interpretacji ani własnych reguł do tego rejestru.

Jeżeli masz propozycję nowej dobrej praktyki, zapytaj użytkownika bezpośrednio w rozmowie. Zapisz ją dopiero po jego wyraźnej zgodzie. Nie twórz rejestru, listy, pliku ani zgłoszenia oczekującego na zatwierdzenie.

Sprawdzaj błędy dotyczące projektu w rejestrze https://github.com/Pawel-BoOssko/fault-harbor . Zgłaszaj błędy przez dostępny MCP `fault-harbor` lub lokalny klient z trwałą kolejką, w zwykłym tekście.

To wyłącznie odnośniki do źródeł. Istniejące zasady projektu pozostają w mocy.
<!-- KONIEC DOBRE-PRAKTYKI-FAULT-HARBOR-GPT6-20261113 -->
