# MCP_NICK: obowiązkowy kontrakt walidacji we wszystkich projektach MCP

**Data utworzenia:** 13.11.2026, 04:14:06 (Europe/Warsaw). **Autor:** GPT-6.  
**Powód:** usunięcie błędów, w których narzędzia sprawdzały słownik NATO, odrzucały „NOVA” lub wymagały ponownego nadania nicku już rozpoznanej sesji.

## Jedyna dopuszczalna kontrola składni

Deklaracja widoczna dla czatu ma mieć postać:

`@@@MCP_NICK:` + **od 7 do 20 liter** + **dokładnie trzy cyfry ASCII od 0 do 9** + `@@@`.

Wartość wewnątrz znacznika można zwalidować wyrażeniem `^[\p{L}]{7,20}[0-9]{3}$` (JavaScript, flaga `u`). Pełna deklaracja: `^@@@MCP_NICK:([\p{L}]{7,20})([0-9]{3})@@@$` (flaga `u`). W Pythonie: sprawdź 7–20 znaków `isalpha()` i następnie 3 znaki z zakresu `0`–`9`; nie używaj `str.isdigit()` samodzielnie do akceptowania innych znaków cyfr.

**POPRAWNE**: `@@@MCP_NICK:NOVAECHOROMEO742@@@`, `@@@MCP_NICK:ALPHALIMASIERRA583@@@`, `@@@MCP_NICK:ABCDEFG123@@@`. Litery nie muszą tworzyć rzeczywistych słów, nie muszą być wielkie i nie są ograniczone do ASCII.

**NIEDOPUSZCZALNE KONTROLE**:
- Sprawdzanie słów względem alfabetu NATO, słowników, ortografii, semantyki, podziału na trzy słowa lub liczby słów.
- Odrzucanie `NOVA`, `ALPHA` lub dowolnego innego fragmentu literowego tylko dlatego, że nie jest pełną nazwą NATO.
- Żądanie od czatu nowego pseudonimu, jeśli centralny rejestr już wiąże autentyczny `MCP_ID` z `MCP_NICK`.
- Dodatkowe, lokalne sprawdzanie „własności nicku” poza centralnymi powiązaniami. Nie wymyślaj dodatkowych warunków akceptacji.

Instrukcja **generowania** nicku może sugerować sklejenie trzech słów, lecz taki sposób generowania **nie jest** regułą walidacyjną. Wynik sprawdza się wyłącznie syntaktycznie.

## Komunikaty błędu: obowiązkowo konkretne

Przy odrzuceniu wskaż dokładny powód, np. „brak prefiksu `@@@MCP_NICK:`”, „brak trzech końcowych `@@@`”, „6 liter, wymagane 7–20”, „21 liter, wymagane 7–20”, „2 cyfry, wymagane dokładnie 3”, „niedozwolony znak” albo „cyfry nie są na końcu”. Nie pisz „niepoprawny nick” bez wyjaśnienia. `NOVA` **nigdy** nie jest samo w sobie powodem odrzucenia.

## Procedura rejestracji i nieblokowanie pracy

1. Na podstawie oryginalnego `MCP_ID` odczytaj centralne powiązanie z Neo4j; jeśli `MCP_NICK` istnieje, użyj go bez kolejnego pytania ani zmiany.
2. Jeśli baza potwierdza brak powiązania, dopiero wtedy poproś o deklarację `@@@MCP_NICK:...@@@`.
3. Sprawdź wyłącznie powyższą składnię. Wyślij prawdziwe `MCP_ID` i deklarowany nick do centralnego rejestru; konflikty rozstrzyga wyłącznie ten rejestr.
4. Zwróć wszystkie znane spośród `UUID`, `UI_NAME`, `MCP_ID`, `MCP_NICK`. Brak UUID/nazwy nie blokuje pracy. Jeśli baza jest niedostępna, odróżnij awarię od braku rejestracji. **Żaden błąd rejestracji nie blokuje wykonywania zwykłych poleceń MCP na komputerach.**

## Minimalne testy odbiorowe

Testy muszą zaakceptować: `NOVAECHOROMEO742`, `ALPHALIMASIERRA583`, siedem i dwadzieścia liter, dowolne kombinacje liter, trzy cyfry. Muszą odrzucić: sześć/dwadzieścia jeden liter, dwie/cztery cyfry, niepoprawne znaczniki, spacje lub znaki inne niż litery w polu literowym, cyfry w środku liter. Każda odmowa ma zawierać przyczynę. Test powtórnego kontaktu ma odzyskiwać istniejący nick po `MCP_ID` bez ponownego generowania.

Ta instrukcja zastępuje starsze zapisy żądające dokładnie trzech słów NATO lub sprawdzania ich ze słownikiem. Nie zmieniaj działania innych funkcji MCP bez potrzeby.